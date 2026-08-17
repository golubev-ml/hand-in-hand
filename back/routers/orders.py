"""Заказы: покупка рисунков с отправкой письма покупателю."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from mail import build_order_html, send_email
from models import Order, Picture, Log
from schemas import PictureOrderCreate, OrderOut
from archive import archive_expired

router = APIRouter(prefix="/api/orders", tags=["Заказы"])


@router.post("", response_model=OrderOut, status_code=201)
def create_order(data: PictureOrderCreate, response: Response, db: Session = Depends(get_db)):
    """HIH-1: цену выбирает покупатель (не ниже min_price); картины уникальны."""

    # ленивая чистка: sold старше недели -> archive
    archive_expired(db)

    ids = [it.picture_id for it in data.items]
    pictures = db.query(Picture).filter(Picture.id.in_(ids)).all()
    if len(pictures) != len(ids):
        raise HTTPException(status_code=400, detail="Одна или более картин не найдены")
    by_id = {p.id: p for p in pictures}

    # доступность и валидация цен — ТОЛЬКО сервером
    for it in data.items:
        p = by_id[it.picture_id]
        if p.status == "sold" or p.order_id is not None:
            raise HTTPException(status_code=400, detail=f"Картина '{p.title}' уже продана или недоступна")
        if it.offered_price < p.min_price:
            raise HTTPException(status_code=400, detail=f"Минимальная цена для '{p.title}' — {int(p.min_price)} ₽")

    total = sum(it.offered_price for it in data.items)
    payment_status = "failed" if data.customer_phone == "78889990002" else "paid"

    items_snapshot = [
        {
            "id": by_id[it.picture_id].id,
            "title": by_id[it.picture_id].title,
            "author": by_id[it.picture_id].author,
            "age": by_id[it.picture_id].age,
            "price": it.offered_price,
            "description": by_id[it.picture_id].description,
        }
        for it in data.items
    ]

    email_status = "not_sent"
    if payment_status == "paid":
        try:
            mail_items = [
                {
                    "img": by_id[it.picture_id].image_path,
                    "title": by_id[it.picture_id].title,
                    "story": by_id[it.picture_id].history,
                    "price": it.offered_price,
                    "qty": 1,
                }
                for it in data.items
            ]
            html = build_order_html(name=data.customer_name, items=mail_items, total=total)
            send_email(
                data.customer_email,
                "Искусство чтобы жить — спасибо за вашу покупку!",
                html,
                items=mail_items,
            )
            email_status = "sent"
        except Exception as e:
            print(f">>> Не удалось отправить письмо: {e}")
            email_status = "failed"

    order = Order(
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        customer_phone=data.customer_phone,
        total=total,
        payment_status=payment_status,
        email_status=email_status,
        items=items_snapshot,
    )
    db.add(order)
    db.flush()

    if payment_status == "paid":
        now = datetime.now()
        for it in data.items:
            p = by_id[it.picture_id]
            p.status = "sold"
            p.order_id = order.id
            p.sold_at = now

    db.add(Log(
        text=f"ORDER → {data.customer_email} ({payment_status})",
        url="/api/orders",
        request=f"items={len(data.items)}, total={total}, phone={data.customer_phone}",
        response=f"payment_status={payment_status}, email_status={email_status}",
    ))
    db.commit()

    if payment_status == "failed":
        response.status_code = 402

    return OrderOut(
        order_id=order.id,
        payment_status=payment_status,
        email_status=email_status,
        total=total,
    )