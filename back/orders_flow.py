"""HIH-9: жизненный цикл заказа при реальной оплате.

Общая логика для POST /api/orders, /payment/return, /payment/fail и отмены в админке:
резерв картин, перевод в sold по подтверждению шлюза, снятие резерва при провале,
письмо покупателю. Оплату подтверждает ТОЛЬКО ответ getOrderStatus.do.
"""
from datetime import datetime

import settings_store
from models import Order, Picture


def reserve_pictures(db, order: Order, picture_ids: list[int]) -> None:
    """Картины закрепляются за заказом через order_id, но остаются available,
    пока платёж не подтверждён (в продажу их не пустит проверка order_id)."""
    now = datetime.now()
    for picture in db.query(Picture).filter(Picture.id.in_(picture_ids)).all():
        picture.order_id = order.id
        picture.status_changed_at = now
    db.commit()


def mark_paid(db, order: Order) -> bool:
    """paid по ответу шлюза. Идемпотентно: False, если заказ уже обработан."""
    if order.payment_status == "paid":
        return False
    now = datetime.now()
    order.payment_status = "paid"
    for picture in db.query(Picture).filter(Picture.order_id == order.id).all():
        picture.status = "sold"
        picture.sold_at = now
        picture.status_changed_at = now
    db.commit()
    return True


def release_reservation(db, order: Order, status: str = "failed", cancel: bool = False) -> None:
    """Снимает резерв с картин (отказ платежа или отмена администратором)."""
    now = datetime.now()
    order.payment_status = status
    if cancel:
        order.cancelled_at = now
    for picture in db.query(Picture).filter(Picture.order_id == order.id).all():
        picture.order_id = None
        picture.sold_at = None
        if picture.status != "archive":
            picture.status = "available"
        picture.status_changed_at = now
    db.commit()


def send_receipt(db, order: Order) -> str:
    """Письмо покупателю: только после paid и только при включённом флаге."""
    if order.payment_status != "paid":
        return order.email_status
    if not settings_store.email_after_purchase(db):
        order.email_status = "not_sent"
        db.commit()
        return order.email_status

    from mail import EMAIL_ENABLED, build_order_html, send_email

    if not EMAIL_ENABLED:
        return order.email_status

    pictures = db.query(Picture).filter(Picture.order_id == order.id).all()
    price_by_id = {it.get("id"): it.get("price", 0) for it in (order.items or [])}
    mail_items = [
        {
            "img": p.image_path,
            "title": p.title or f"Рисунок #{p.id}",
            "story": p.history or "",
            "price": price_by_id.get(p.id, 0),
            "qty": 1,
        }
        for p in pictures
    ]
    if not mail_items:  # резерва нет (ручной sold/старые данные) — письмо без карточек
        mail_items = [{"img": "", "title": it.get("title", ""), "story": "",
                       "price": it.get("price", 0), "qty": 1} for it in (order.items or [])]
    if not mail_items:
        return order.email_status

    try:
        html = build_order_html(name=order.customer_name, items=mail_items, total=order.total)
        send_email(
            order.customer_email,
            "Искусство чтобы жить — спасибо за вашу покупку!",
            html,
            items=[m for m in mail_items if m["img"].startswith("/uploads/")],
        )
        order.email_status = "sent"
    except Exception as exc:  # noqa: BLE001 — письмо не должно ронять оплату
        print(f">>> Не удалось отправить письмо: {exc}")
        order.email_status = "failed"
    db.commit()
    return order.email_status


def apply_gateway_status(db, order: Order, status: dict) -> dict:
    """Применяет результат getOrderStatus.do к заказу с сверкой суммы и номера.

    Возвращает {status, verified, reason}. paid ставится только если шлюз вернул
    статус 2 И (если вернул) сумму и номер заказа, совпадающие с заказом в БД.
    """
    expected_kopecks = int(round(float(order.total) * 100))
    reason = ""

    if status.get("order_number") not in (None, "") and str(status["order_number"]) != str(order.id):
        return {"status": order.payment_status, "verified": False,
                "reason": f"orderNumber шлюза {status['order_number']} != заказ {order.id}"}

    if status.get("amount") not in (None, ""):
        try:
            gateway_amount = int(round(float(status["amount"])))
        except (TypeError, ValueError):
            return {"status": order.payment_status, "verified": False,
                    "reason": f"шлюз вернул нечисловую сумму {status['amount']!r}"}
        if gateway_amount != expected_kopecks:
            return {"status": order.payment_status, "verified": False,
                    "reason": f"сумма шлюза {gateway_amount} ≠ {expected_kopecks} копеек заказа"}

    new_status = status["status"]
    if new_status == "paid":
        changed = mark_paid(db, order)
        reason = "paid" if changed else "уже обработан ранее (идемпотентно)"
        if changed:
            send_receipt(db, order)
    elif new_status == "failed":
        release_reservation(db, order, "failed")
        reason = "платёж отклонён шлюзом"
    else:
        reason = "платёж ещё не завершён — статус не меняем"

    return {"status": new_status, "verified": True, "reason": reason}
