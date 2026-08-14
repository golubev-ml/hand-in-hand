import json
import os
import secrets
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from auth import hash_password
from database import Base, SessionLocal, engine
from models import Log, Manager
from routers import auth_router, donations, logs, orders, pictures

from admin_panel import router as admin_router

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "local")  # local | test | prod

ADMIN_LOGIN = os.getenv("ADMIN_LOGIN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if APP_ENV in ("test", "prod"):
    # на тесте/проде без секретов приложение падает — как требует Максим
    _missing = [n for n, v in (("ADMIN_LOGIN", ADMIN_LOGIN),
                               ("ADMIN_PASSWORD", ADMIN_PASSWORD)) if not v]
    if _missing:
        raise RuntimeError(f"APP_ENV={APP_ENV}: не заданы секреты: {', '.join(_missing)}")
else:
    # локальная разработка: пароль генерируется и виден только в логах
    ADMIN_LOGIN = ADMIN_LOGIN or "hand_admin"
    if not ADMIN_PASSWORD:
        ADMIN_PASSWORD = secrets.token_urlsafe(12)
        print(f">>> DEV: временный админ {ADMIN_LOGIN} / {ADMIN_PASSWORD}")

FRONT_DIR = next(
    (
        path
        for path in (
            Path(__file__).resolve().parent.parent / "front",
            Path(__file__).resolve().parent / "front",
            Path("/app/front"),
        )
        if path.exists()
    ),
    Path("/app/front"),
)
FRONT_BUILD_DIR = FRONT_DIR / "dist"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        if not db.query(Manager).filter(Manager.login == ADMIN_LOGIN).first():
            db.add(Manager(login=ADMIN_LOGIN, password_hash=hash_password(ADMIN_PASSWORD)))
            db.commit()
            print(f">>> Создан администратор: {ADMIN_LOGIN}")
    finally:
        db.close()
    yield


app = FastAPI(title="Gallery API", lifespan=lifespan)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ─── Rate Limiter (in-memory по IP) ───────────────────────────────────────────
# Простой механизм без зависимостей: для POST /api/orders и /admin/login
RATE_LIMITS = defaultdict(list)  # {ip: [timestamp, ...]}
RATE_LIMIT_REQUESTS = 5  # макс 5 запросов
RATE_LIMIT_WINDOW_SECONDS = 60  # за 60 секунд


def _get_client_ip(request: Request) -> str:
    """Получить IP клиента (с учётом прокси)."""
    if forwarded := request.headers.get("x-forwarded-for"):
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str, path: str) -> bool:
    """Проверить rate limit. Возвращает True если запрос разрешён."""
    now = datetime.now()
    key = f"{ip}:{path}"
    
    # Очищаем старые запросы за пределами окна
    RATE_LIMITS[key] = [
        ts for ts in RATE_LIMITS[key] 
        if now - ts < timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    ]
    
    if len(RATE_LIMITS[key]) >= RATE_LIMIT_REQUESTS:
        return False
    
    RATE_LIMITS[key].append(now)
    return True


# ─── CORS ─────────────────────────────────────────────────────────────────────
# ориджины доменом; в local разрешаем dev-серверы (vite, предпросмотры).
if APP_ENV == "local":
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", BASE_URL).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API-роутеры
app.include_router(auth_router.router)
app.include_router(pictures.router)
app.include_router(orders.router)
app.include_router(donations.router)
app.include_router(logs.router)
app.include_router(admin_router)

# Загруженные картинки доступны по /uploads/<файл>
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def _redact(text: str) -> str:
    """Прячем пароли и карты в логе."""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            for key in ("password", "card"):
                if key in data:
                    data[key] = "***"
            return json.dumps(data, ensure_ascii=False)[:2000]
    except (ValueError, TypeError):
        pass
    return text[:2000]


@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = b""
    if request.url.path.startswith("/api"):
        try:
            body = await request.body()
        except Exception:
            body = b""

    # Rate limiting для чувствительных эндпоинтов
    if request.method == "POST" and request.url.path in ("/api/orders", "/admin/login"):
        ip = _get_client_ip(request)
        if not _check_rate_limit(ip, request.url.path):
            return JSONResponse(
                {"detail": "Слишком много запросов. Попробуйте позже."},
                status_code=429,
            )

    response = await call_next(request)

    # Логируем только /api, чтобы статика не засоряла базу
    if request.url.path.startswith("/api"):
        db = SessionLocal()
        try:
            db.add(Log(
                text=f"{request.method} → {response.status_code}",
                time=datetime.now(),
                url=request.url.path + (f"?{request.url.query}" if request.url.query else ""),
                request=_redact(body.decode(errors="ignore")),
                response=f"HTTP {response.status_code}",
            ))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    return response


@app.get("/api/health", tags=["Сервис"])
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ---------- Раздача фронтенда из папки front/ ----------
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    base_dir = FRONT_BUILD_DIR if FRONT_BUILD_DIR.exists() and FRONT_BUILD_DIR.is_dir() else FRONT_DIR
    candidate = (base_dir / full_path).resolve()
    if candidate.is_file() and candidate.is_relative_to(base_dir):
        return FileResponse(candidate)
    index = base_dir / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"status": "ok", "message": "API работает, документация на /docs"})
