"""Заказы: покупка рисунков. HIH-9 — два режима: заглушка (оплата ВЫКЛ) и шлюз Сбербанка."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

import orders_flow
import settings_store
from archive import archive_expired
from database import get_db
from models import Log, Order, Picture
from payments import sber
from schemas import OrderOut, PictureOrderCreate

router = APIRouter(prefix="/api/orders", tags=["Заказы"])

# Старая тестовая заглушка: этот номер телефона означал «платёж отклонён»
PHONE_FAIL = "78889990002"


@router.post("", response_model=OrderOut, status_code=201)
def create_order(data: PictureOrderCreate, response: Response, db: Session = Depends(get_db)):
    """HIH-1: цену выбирает покупатель (не ниже min_price); картины уникальны.

    HIH-9: если в админке включена оплата — заказ создаётся pending, картины
    резервируются, покупателю отдаётся payment_url для редиректа в шлюз Сбера.
    Если выключена — работает прежняя схема-заглушка (paid сразу).
    """
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
    payments_on = settings_store.payments_enabled(db)
    if payments_on and not sber.is_configured(db):
        raise HTTPException(
            status_code=503,
            detail="Оплата включена, но учётные данные шлюза не заданы — заполните /admin/settings",
        )

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

    order = Order(
        created_at=datetime.now(),
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        customer_phone=data.customer_phone,
        total=total,
        payment_status="pending",
        email_status="not_sent",
        items=items_snapshot,
    )
    db.add(order)
    db.flush()

    payment_url = ""

    if payments_on:
        # Реальный платёж: резервируем картины, статус решит getOrderStatus.do
        orders_flow.reserve_pictures(db, order, ids)
        try:
            payment = sber.create_payment(
                order_number=order.id,
                amount_rub=total,
                method=data.payment_method,
                db=db,
                description="Оплата рисунков — фонд «Рука об руку»",
            )
        except sber.SberError as exc:
            orders_flow.release_reservation(db, order, status="failed")
            db.add(Log(text=f"ORDER {order.id} → шлюз отказал при регистрации",
                       url="/api/orders", request=f"total={total}, method={data.payment_method}",
                       response=str(exc)[:2000]))
            db.commit()
            raise HTTPException(status_code=502, detail=f"Платёжный шлюз недоступен: {exc}") from exc

        order.sber_order_id = str(payment["order_id"] or "")[:64] or None
        payment_url = payment["payment_url"]
        db.commit()
    elif data.customer_phone == PHONE_FAIL:
        # Старая схема: «отклонённый» платёж — картины остаются в продаже
        order.payment_status = "failed"
        db.commit()
        response.status_code = 402
    else:
        # Старая схема: paid сразу, картины проданы, письмо по флагу настроек
        orders_flow.reserve_pictures(db, order, ids)
        orders_flow.mark_paid(db, order)
        orders_flow.send_receipt(db, order)

    db.add(Log(
        text=f"ORDER → {data.customer_email} ({order.payment_status})",
        url="/api/orders",
        request=f"items={len(data.items)}, total={total}, phone={data.customer_phone}, "
                f"method={data.payment_method}, payments={'on' if payments_on else 'off'}",
        response=f"payment_status={order.payment_status}, email_status={order.email_status}, "
                 f"sber_order_id={order.sber_order_id}",
    ))
    db.commit()

    if order.payment_status == "failed":
        response.status_code = 402

    return OrderOut(
        order_id=order.id,
        payment_status=order.payment_status,
        email_status=order.email_status,
        total=order.total,
        payment_url=payment_url,
        order_number=str(order.id),
    )
