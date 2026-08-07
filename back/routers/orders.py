"""Заказы: покупка рисунков с отправкой письма покупателю."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from mail import build_order_html, send_email
from models import Log
from schemas import OrderCreate

router = APIRouter(prefix="/api/orders", tags=["Заказы"])


@router.post("")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    total = sum(i.price * i.qty for i in order.items)

    html = build_order_html(
        name=order.name,
        items=[i.model_dump() for i in order.items],
        total=total,
    )
    try:
        send_email(
            order.email,
            "Краски детства — спасибо за вашу покупку!",
            html,
            items=[i.model_dump() for i in order.items],
        )
        sent = True
    except Exception as e:  # не ломаем заказ, если почта временно недоступна
        print(">>> Не удалось отправить письмо:", e)
        sent = False

    db.add(Log(
        text=f"ORDER → {order.email}",
        url="/api/orders",
        request=f"items={len(order.items)}, total={total}",
        response="email sent" if sent else "email failed",
    ))
    db.commit()

    return {"status": "ok", "total": total, "email_sent": sent}
