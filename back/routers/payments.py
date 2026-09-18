"""HIH-9: заказы через платёжный шлюз Сбербанка (тестовый контур ecomm).

Общий модуль для маршрутов возврата/отказа оплаты: /payment/return и /payment/fail.

Главное правило: платёж подтверждает только ответ getOrderStatus.do. Данные из
браузера (query-параметры returnUrl) используются лишь для того, чтобы НАЙТИ заказ,
и никогда — чтобы присвоить ему статус.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

import orders_flow
from payments import sber
from database import get_db
from models import Log, Order

router = APIRouter(prefix="/payment", tags=["Оплата"])

# Куда уводить покупателя после обработки возврата (фронт читает параметр payment)
REDIRECTS = {
    "paid": "/?payment=success",
    "failed": "/?payment=failed",
    "pending": "/?payment=pending",
    "unknown": "/?payment=unknown",
}


def _find_order(db: Session, params) -> Order | None:
    """Ищем заказ по параметрам возврата. Только поиск — статус решит шлюз."""
    for name in ("merchantOrderId", "mercahntOrderId", "merchant_order_id", "orderNumber", "orderId"):
        value = params.get(name)
        if not value:
            continue
        if str(value).isdigit():
            order = db.get(Order, int(value))
            if order:
                return order
        order = db.query(Order).filter(Order.sber_order_id == str(value)).first()
        if order:
            return order
    return None


def _handle(request: Request, db: Session, fallback: str):
    order = _find_order(db, request.query_params)

    if order is None:
        db.add(Log(text="PAYMENT → заказ не найден по параметрам возврата",
                   url=request.url.path, request=str(dict(request.query_params))[:2000],
                   response=f"redirect {REDIRECTS['unknown']}"))
        db.commit()
        return RedirectResponse(REDIRECTS["unknown"], status_code=302)

    # Идемпотентность: уже оплаченный заказ повторно не обрабатываем
    if order.payment_status == "paid":
        db.add(Log(text=f"PAYMENT {order.id} → уже paid, повторная обработка пропущена",
                   url=request.url.path, request=str(dict(request.query_params))[:2000],
                   response="noop"))
        db.commit()
        return RedirectResponse(REDIRECTS["paid"], status_code=302)

    try:
        status = sber.get_status(order.id, db=db)
    except sber.SberError as exc:
        result = {"status": order.payment_status, "verified": False,
                  "reason": f"шлюз не ответил: {exc}"}
    else:
        result = orders_flow.apply_gateway_status(db, order, status)
        if status.get("order_id") and not order.sber_order_id:
            order.sber_order_id = str(status["order_id"])
            db.commit()

    db.add(Log(
        text=f"PAYMENT {order.id} ({request.url.path}) → {order.payment_status}",
        url=request.url.path + (f"?{request.url.query}" if request.url.query else ""),
        request=str(dict(request.query_params))[:2000],
        response=f"{result['status']}: {result['reason']}"[:2000],
    ))
    db.commit()

    # Статус заказа мог измениться только по ответу шлюза — на него и ориентируемся.
    if order.payment_status == "paid":
        target = "paid"
    elif fallback == "fail" or result["status"] == "failed":
        target = "failed"
    else:
        target = "pending"
    return RedirectResponse(REDIRECTS[target], status_code=302)


@router.get("/return")
def payment_return(request: Request, db: Session = Depends(get_db)):
    """Возврат покупателя с платёжной страницы (успех или не успех — решает шлюз)."""
    return _handle(request, db, fallback="return")


@router.get("/fail")
def payment_fail(request: Request, db: Session = Depends(get_db)):
    """Возврат покупателя по failUrl: тоже сверяемся со шлюзом, потом решаем статус."""
    return _handle(request, db, fallback="fail")
