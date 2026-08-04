import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_manager
from database import get_db
from models import Donation, Manager
from schemas import DonationCreate, DonationOut, DonationStatusUpdate

router = APIRouter(prefix="/api/donations", tags=["Пожертвования"])


def mask_card(card: str) -> str:
    """Храним ТОЛЬКО последние 4 цифры. Полный номер карты хранить нельзя."""
    digits = re.sub(r"\D", "", card)
    if len(digits) < 12:
        raise HTTPException(status_code=400, detail="Некорректный номер карты")
    return f"**** **** **** {digits[-4:]}"


@router.post("", response_model=DonationOut, status_code=201)
def create_donation(data: DonationCreate, db: Session = Depends(get_db)):
    """Публичный эндпоинт — его вызывает форма пожертвования на сайте."""
    payload = data.model_dump()
    if payload.get("date") is None:
        payload.pop("date")
    payload["card"] = mask_card(payload["card"])
    donation = Donation(**payload)
    db.add(donation)
    db.commit()
    db.refresh(donation)
    return donation


@router.get("", response_model=list[DonationOut])
def list_donations(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    query = db.query(Donation)
    if status:
        query = query.filter(Donation.status == status)
    return query.order_by(Donation.time.desc()).all()


@router.patch("/{donation_id}/status", response_model=DonationOut)
def update_status(
    donation_id: int,
    data: DonationStatusUpdate,
    db: Session = Depends(get_db),
    _: Manager = Depends(get_current_manager),
):
    donation = db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Пожертвование не найдено")
    if data.status not in ("pending", "confirmed", "rejected"):
        raise HTTPException(status_code=400, detail="Недопустимый статус")
    donation.status = data.status
    db.commit()
    db.refresh(donation)
    return donation