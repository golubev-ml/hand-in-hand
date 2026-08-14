"""Админка сайта: /admin. Чистый FastAPI, без сторонних админок."""
import html
import os
import uuid
from pathlib import Path
from PIL import Image

import jwt
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from jwt.exceptions import PyJWTError
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY, create_token, verify_password
from database import get_db
from models import Donation, Log, Manager, Order, Picture

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


router = APIRouter(prefix="/admin", include_in_schema=False)


@router.get("", include_in_schema=False)
def admin_root_redirect():
    return RedirectResponse("/admin/", status_code=302)


def current_admin(request: Request) -> str:
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return payload.get("login", "")


TEMPLATE = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>@TITLE@</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#f6f7f9;color:#111}
header{background:#111827;color:#fff;padding:12px 20px;display:flex;gap:16px;align-items:center}
header a{color:#93c5fd;text-decoration:none}
main{padding:20px;max-width:1100px;margin:0 auto}
table{border-collapse:collapse;width:100%;background:#fff}
td,th{border:1px solid #e5e7eb;padding:8px 10px;text-align:left;font-size:14px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:16px}
input,select,button,textarea{padding:8px 10px;margin:4px 0;font-size:14px}
button{cursor:pointer}
img.thumb{width:60px;height:60px;object-fit:cover}
</style></head><body>
<header><b>Админка</b>
<a href="/admin/">Статистика</a>
<a href="/admin/pictures">Рисунки</a>
<a href="/admin/pictures/upload">+ Картинка</a>
<a href="/admin/orders">Заказы</a>
<a href="/admin/donations">Пожертвования</a>
<a href="/admin/logs">Лог</a>
<span style="margin-left:auto">@LOGIN@ · <a href="/admin/logout">выйти</a></span>
</header><main>@BODY@</main></body></html>"""


def page(title: str, body: str, login: str) -> str:
    return TEMPLATE.replace("@TITLE@", title).replace("@BODY@", body).replace("@LOGIN@", login)


LOGIN_PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Вход</title>
<style>body{font-family:system-ui,sans-serif;background:#f6f7f9;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
form{background:#fff;padding:24px 28px;border:1px solid #e5e7eb;border-radius:10px;display:flex;flex-direction:column}
input{margin:6px 0;padding:9px 10px}button{margin-top:10px;padding:10px;cursor:pointer}</style></head>
<body><form method="post" action="/admin/login"><h2>Вход в админку</h2>
<input name="login" placeholder="Логин" required>
<input name="password" type="password" placeholder="Пароль" required>
<button>Войти</button></form></body></html>"""


# ---------- вход / выход ----------
@router.get("/login", response_class=HTMLResponse)
def login_page():
    return LOGIN_PAGE


@router.post("/login")
def do_login(login: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    manager = db.query(Manager).filter(Manager.login == login).first()
    if not manager or manager.status != "active" or not verify_password(password, manager.password_hash):
        return HTMLResponse(
            LOGIN_PAGE.replace("<button>", "<p style='color:#b91c1c'>Неверный логин или пароль</p><button>"),
            status_code=401,
        )
    response = RedirectResponse("/admin/", status_code=302)
    response.set_cookie(
        "admin_token",
        create_token(manager.id, manager.login),
        httponly=True,
        max_age=12 * 3600,
        samesite="lax",
        secure=os.getenv("APP_ENV", "local") != "local",
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie("admin_token")
    return response


# ---------- статистика ----------
@router.get("/", response_class=HTMLResponse)
def dashboard(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    pic_total = db.query(func.count(Picture.id)).scalar() or 0
    pic_avail = db.query(func.count(Picture.id)).filter(Picture.status == "available").scalar() or 0
    pic_sold = db.query(func.count(Picture.id)).filter(Picture.status == "sold").scalar() or 0
    don_total = db.query(func.count(Donation.id)).scalar() or 0
    don_sum = db.query(func.sum(Donation.price)).filter(Donation.status == "confirmed").scalar() or 0
    man_total = db.query(func.count(Manager.id)).scalar() or 0
    log_total = db.query(func.count(Log.id)).scalar() or 0
    body = f"""<h2>Статистика</h2><div class="card"><table>
    <tr><th>Рисунков всего</th><td>{pic_total}</td></tr>
    <tr><th>Доступно / продано</th><td>{pic_avail} / {pic_sold}</td></tr>
    <tr><th>Пожертвований</th><td>{don_total}</td></tr>
    <tr><th>Сумма подтверждённых пожертвований</th><td>{don_sum} ₽</td></tr>
    <tr><th>Менеджеров</th><td>{man_total}</td></tr>
    <tr><th>Записей в логе</th><td>{log_total}</td></tr>
    </table></div>"""
    return page("Статистика", body, login)


# ---------- рисунки ----------
@router.get("/pictures", response_class=HTMLResponse)
def pictures(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(Picture).order_by(Picture.time.desc()).all()
    tr = ""
    for p in rows:
        title = html.escape(getattr(p, "title", "") or f"#{p.id}")
        author = html.escape(getattr(p, "author", "") or "—")
        age = getattr(p, "age", 0) or "—"
        tr += f"""<tr>
        <td><img class="thumb" src="{p.image_path}"></td>
        <td>{title}</td><td>{author}</td><td>{age}</td><td>{p.price} ₽</td>
        <td><form method="post" action="/admin/pictures/{p.id}/status" style="margin:0">
            <select name="status" onchange="this.form.submit()">
                <option {'selected' if p.status == 'available' else ''}>available</option>
                <option {'selected' if p.status == 'sold' else ''}>sold</option>
                <option {'selected' if p.status == 'archive' else ''}>archive</option>
            </select></form></td>
        <td><form method="post" action="/admin/pictures/{p.id}/delete" style="margin:0"><button>удалить</button></form></td>
        </tr>"""
    body = f"""<h2>Рисунки</h2><div class="card"><table>
    <tr><th>Превью</th><th>Название</th><th>Имя ребёнка</th><th>Возраст</th><th>Цена</th><th>Статус</th><th></th></tr>{tr}</table></div>"""
    return page("Рисунки", body, login)


@router.get("/pictures/upload", response_class=HTMLResponse)
def upload_form(login: str = Depends(current_admin)):
    body = """<h2>Загрузка рисунка</h2><div class="card">
    <form method="post" action="/admin/pictures/upload" enctype="multipart/form-data">
    <input type="file" name="file" accept="image/*" required><br>
    <input name="title" placeholder="Название" style="width:100%"><br>
    <input name="author" placeholder="Имя ребёнка" maxlength="100" required style="width:100%"><br>
    <input name="age" type="number" min="1" max="18" placeholder="Возраст" required style="width:100%"><br>
    <textarea name="history" placeholder="История рисунка" style="width:100%" rows="3"></textarea><br>
    <input name="price" type="number" step="0.01" value="0"><br>
    <button>Сохранить</button></form></div>"""
    return page("Загрузка", body, login)


@router.post("/pictures/upload")
async def upload_save(
    file: UploadFile = File(...),
    title: str = Form(""),
    author: str = Form(...),
    age: int = Form(..., ge=1, le=18),
    history: str = Form(""),
    price: float = Form(0.0),
    login: str = Depends(current_admin),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        return HTMLResponse("Формат не поддерживается. <a href='/admin/pictures/upload'>назад</a>", status_code=400)
    
    file_data = await file.read()
    if len(file_data) > MAX_FILE_SIZE:
        return HTMLResponse(f"Файл слишком большой (макс {MAX_FILE_SIZE // (1024*1024)} МБ). <a href='/admin/pictures/upload'>назад</a>", status_code=400)
    
    base = uuid.uuid4().hex
    orig_name = f"{base}{ext}"
    orig_path = UPLOAD_DIR / orig_name
    orig_path.write_bytes(file_data)
    
    # Pillow: ориентация и версии
    orientation = "landscape"
    gallery = mail = mobile = ""
    try:
        with Image.open(orig_path) as img:
            img = Image.open(orig_path)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            w, h = img.size
            orientation = "portrait" if h > w else "landscape"
            
            def save_version(max_dim, suffix):
                ratio = min(max_dim / w, max_dim / h, 1.0)
                if ratio >= 1.0:
                    new = img.copy()
                else:
                    new = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                vname = f"{base}_{suffix}.webp"
                new.save(UPLOAD_DIR / vname, "WEBP", quality=85)
                return f"/uploads/{vname}"
            
            gallery = save_version(800, "gallery")
            mail    = save_version(600, "mail")
            mobile  = save_version(480, "mobile")
    except Exception as e:
        print(f"[upload] Pillow failed: {e}; using original only")
    
    fields = {
        "image_path": f"/uploads/{orig_name}",
        "history": history,
        "price": price,
        "author": author.strip(),
        "age": age,
        "orientation": orientation,
        "image_path_gallery": gallery,
        "image_path_mail": mail,
        "image_path_mobile": mobile,
    }
    if hasattr(Picture, "title"):
        fields["title"] = title
    db.add(Picture(**fields))
    db.commit()
    return RedirectResponse("/admin/pictures", status_code=302)


@router.post("/pictures/{picture_id}/status")
async def picture_status(picture_id: int, request: Request, login: str = Depends(current_admin), db: Session = Depends(get_db)):
    form = await request.form()
    picture = db.get(Picture, picture_id)
    if picture:
        picture.status = form.get("status", picture.status)
        db.commit()
    return RedirectResponse("/admin/pictures", status_code=302)


@router.post("/pictures/{picture_id}/delete")
def picture_delete(picture_id: int, login: str = Depends(current_admin), db: Session = Depends(get_db)):
    picture = db.get(Picture, picture_id)
    if picture:
        db.delete(picture)
        db.commit()
    return RedirectResponse("/admin/pictures", status_code=302)


# ---------- заказы ----------
@router.get("/orders", response_class=HTMLResponse)
def orders(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(Order).order_by(Order.created_at.desc()).all()
    tr = ""
    for o in rows:
        tr += f"""<tr>
        <td>{o.created_at:%m-%d %H:%M}</td>
        <td>{html.escape(o.customer_name)}</td>
        <td>{html.escape(o.customer_email)}</td>
        <td>{html.escape(o.customer_phone)}</td>
        <td>{o.total} ₽</td>
        <td><span style="background:#{'#dcfce7' if o.payment_status == 'paid' else '#fee2e2'};padding:2px 6px;border-radius:3px">{o.payment_status}</span></td>
        <td><span style="background:#{'#dcfce7' if o.email_status == 'sent' else '#fef3c7'};padding:2px 6px;border-radius:3px">{o.email_status}</span></td>
        </tr>"""
    body = f"""<h2>Заказы</h2><div class="card"><table>
    <tr><th>Дата</th><th>Имя</th><th>Email</th><th>Телефон</th><th>Сумма</th><th>Оплата</th><th>Email</th></tr>{tr}</table></div>"""
    return page("Заказы", body, login)


# ---------- пожертвования ----------
@router.get("/donations", response_class=HTMLResponse)
def donations(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(Donation).order_by(Donation.time.desc()).all()
    tr = ""
    for d in rows:
        tr += f"""<tr><td>{d.date}</td><td>{html.escape(d.name)}</td><td>{d.price} ₽</td><td>{d.card}</td>
        <td><form method="post" action="/admin/donations/{d.id}/status" style="margin:0">
            <select name="status" onchange="this.form.submit()">
                <option {'selected' if d.status == 'pending' else ''}>pending</option>
                <option {'selected' if d.status == 'confirmed' else ''}>confirmed</option>
                <option {'selected' if d.status == 'rejected' else ''}>rejected</option>
            </select></form></td></tr>"""
    body = f"""<h2>Пожертвования</h2><div class="card"><table>
    <tr><th>Дата</th><th>Имя</th><th>Сумма</th><th>Карта</th><th>Статус</th></tr>{tr}</table></div>"""
    return page("Пожертвования", body, login)


@router.post("/donations/{donation_id}/status")
async def donation_status(donation_id: int, request: Request, login: str = Depends(current_admin), db: Session = Depends(get_db)):
    form = await request.form()
    donation = db.get(Donation, donation_id)
    if donation:
        donation.status = form.get("status", donation.status)
        db.commit()
    return RedirectResponse("/admin/donations", status_code=302)


# ---------- лог ----------
@router.get("/logs", response_class=HTMLResponse)
def logs(login: str = Depends(current_admin), db: Session = Depends(get_db)):
    rows = db.query(Log).order_by(Log.time.desc()).limit(200).all()
    tr = "".join(
        f"<tr><td>{l.time:%m-%d %H:%M}</td><td>{html.escape(l.text)}</td><td>{html.escape(l.url)}</td></tr>"
        for l in rows
    )
    body = f"""<h2>Лог запросов</h2><div class="card"><table>
    <tr><th>Время</th><th>Запрос</th><th>URL</th></tr>{tr}</table></div>"""
    return page("Лог", body, login)
