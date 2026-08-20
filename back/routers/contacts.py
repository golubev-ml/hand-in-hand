"""HIH-8: обращения из формы обратной связи — сохраняются в БД."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import ContactMessage, Log
from schemas import ContactMessageCreate, ContactMessageOut

router = APIRouter(prefix="/api/contact", tags=["Обращения"])


@router.post("", response_model=ContactMessageOut, status_code=201)
def create_contact(data: ContactMessageCreate, db: Session = Depends(get_db)):
    msg = ContactMessage(name=data.name, email=data.email, message=data.message)
    db.add(msg)
    db.flush()
    db.add(Log(
        text="POST /api/contact → 201",
        url="/api/contact",
        request=f"name={data.name}, email={data.email}, message={len(data.message)} chars",
        response=f"id={msg.id}",
    ))
    db.commit()
    db.refresh(msg)
    return msg
