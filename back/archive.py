"""HIH-1: ленивое архивирование — sold старше недели уходят в archive.

HIH-9: здесь же снимается резерв с картин у заказов, так и не дошедших до оплаты
(покупатель закрыл страницу банка), иначе картина навсегда осталась бы «недоступна».
"""
from datetime import datetime, timedelta

import os

from models import Order, Picture

SOLD_LIFETIME_DAYS = 7
# Сколько минут держим резерв картин над неоплаченным заказом
PENDING_RESERVATION_MINUTES = int(os.getenv("PENDING_RESERVATION_MINUTES", "60"))


def archive_expired(db) -> int:
    """Переводит просроченные sold в archive и освобождает зависшие резервы."""
    release_stale_pending(db)

    cutoff = datetime.now() - timedelta(days=SOLD_LIFETIME_DAYS)
    expired = (
        db.query(Picture)
        .filter(Picture.status == "sold", Picture.sold_at != None, Picture.sold_at < cutoff)  # noqa: E711
        .all()
    )
    for p in expired:
        p.status = "archive"
        p.status_changed_at = datetime.now()
    if expired:
        db.commit()
    return len(expired)


def release_stale_pending(db, minutes: int | None = None) -> int:
    """pending-заказ старше minutes → failed, картины снова в продаже. Возвращает число заказов."""
    minutes = PENDING_RESERVATION_MINUTES if minutes is None else minutes
    cutoff = datetime.now() - timedelta(minutes=minutes)
    stale = (
        db.query(Order)
        .filter(Order.payment_status == "pending", Order.created_at < cutoff,
                Order.cancelled_at == None)  # noqa: E711
        .all()
    )
    if not stale:
        return 0

    from orders_flow import release_reservation  # локальный импорт: нет цикла на старте

    now = datetime.now()
    for order in stale:
        release_reservation(db, order, status="failed")
        order.cancelled_at = now  # помечаем, что заказ закрыт по таймауту
        db.commit()
    return len(stale)
