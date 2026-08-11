import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import PyJWTError
from sqlalchemy.orm import Session

from database import get_db
from models import Manager

SECRET_KEY = os.getenv("SECRET_KEY")
if os.getenv("APP_ENV", "local") in ("test", "prod") and not SECRET_KEY:
    raise RuntimeError("APP_ENV=test/prod: не задан SECRET_KEY")
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key"  # только для local
ALGORITHM = "HS256"
TOKEN_HOURS = 12

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(manager_id: int, login: str) -> str:
    payload = {
        "sub": str(manager_id),
        "login": login,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_manager(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Manager:
    """Проверка JWT. Защищает админские эндпоинты."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Не авторизован")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Токен недействителен или истёк")

    try:
        manager_id = int(payload.get("sub", 0))
    except ValueError:
        raise HTTPException(status_code=401, detail="Некорректный токен")

    manager = db.get(Manager, manager_id)
    if manager is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    if manager.status != "active":
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    return manager