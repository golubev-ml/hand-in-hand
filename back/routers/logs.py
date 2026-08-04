from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_manager
from database import get_db
from models import Log, Manager
from schemas import LogOut

router = APIRouter(prefix="/api/logs", tags=["Лог"])


@router.get("", response_model=list[LogOut])
def list_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    """Лог заполняется автоматически middleware в main.py."""
    limit = max(1, min(limit, 1000))
    return db.query(Log).order_by(Log.time.desc()).limit(limit).all()