import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_manager
from database import get_db
from models import Manager, Picture
from schemas import PictureCreate, PictureOut, PictureUpdate

router = APIRouter(prefix="/api/pictures", tags=["Рисунки"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.get("", response_model=list[PictureOut])
def list_pictures(status: str | None = None, db: Session = Depends(get_db)):
    """Публичный список рисунков. Фильтр: /api/pictures?status=sold"""
    query = db.query(Picture)
    if status:
        query = query.filter(Picture.status == status)
    return query.order_by(Picture.time.desc()).all()


@router.get("/{picture_id}", response_model=PictureOut)
def get_picture(picture_id: int, db: Session = Depends(get_db)):
    picture = db.get(Picture, picture_id)
    if picture is None:
        raise HTTPException(status_code=404, detail="Рисунок не найден")
    return picture


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    _: Manager = Depends(get_current_manager),
):
    """Загрузка картинки. Вернёт путь для поля image_path."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Формат не поддерживается")
    filename = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / filename).write_bytes(await file.read())
    return {"image_path": f"/uploads/{filename}"}


@router.post("", response_model=PictureOut, status_code=201)
def create_picture(
    data: PictureCreate,
    db: Session = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    payload = data.model_dump()
    if payload.get("time") is None:
        payload.pop("time")  # тогда сработает default=now
    picture = Picture(**payload)
    db.add(picture)
    db.commit()
    db.refresh(picture)
    return picture


@router.put("/{picture_id}", response_model=PictureOut)
def update_picture(
    picture_id: int,
    data: PictureUpdate,
    db: Session = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    picture = db.get(Picture, picture_id)
    if picture is None:
        raise HTTPException(status_code=404, detail="Рисунок не найден")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(picture, field, value)
    db.commit()
    db.refresh(picture)
    return picture


@router.delete("/{picture_id}", status_code=204)
def delete_picture(
    picture_id: int,
    db: Session = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    picture = db.get(Picture, picture_id)
    if picture is None:
        raise HTTPException(status_code=404, detail="Рисунок не найден")
    db.delete(picture)
    db.commit()