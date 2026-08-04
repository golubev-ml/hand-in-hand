from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import create_token, get_current_manager, hash_password, verify_password
from database import get_db
from models import Manager
from schemas import ManagerCreate, ManagerOut, ManagerStatusUpdate, Token

router = APIRouter(prefix="/api/auth", tags=["Менеджеры"])


@router.post("/register", response_model=ManagerOut, status_code=201)
def register(data: ManagerCreate, db: Session = Depends(get_db)):
    """Создание менеджера. В продакшене этот эндпоинт нужно закрыть!"""
    if db.query(Manager).filter(Manager.login == data.login).first():
        raise HTTPException(status_code=400, detail="Логин уже занят")
    manager = Manager(login=data.login, password_hash=hash_password(data.password))
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return manager


@router.post("/login", response_model=Token)
def login(data: ManagerCreate, db: Session = Depends(get_db)):
    manager = db.query(Manager).filter(Manager.login == data.login).first()
    if manager is None or not verify_password(data.password, manager.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if manager.status != "active":
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    return Token(access_token=create_token(manager.id, manager.login))


@router.get("/me", response_model=ManagerOut)
def me(manager: Manager = Depends(get_current_manager)):
    return manager


@router.patch("/{manager_id}/status", response_model=ManagerOut)
def update_status(
    manager_id: int,
    data: ManagerStatusUpdate,
    db: Session = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    manager = db.get(Manager, manager_id)
    if manager is None:
        raise HTTPException(status_code=404, detail="Менеджер не найден")
    if data.status not in ("active", "blocked"):
        raise HTTPException(status_code=400, detail="Статус: 'active' или 'blocked'")
    manager.status = data.status
    db.commit()
    db.refresh(manager)
    return manager