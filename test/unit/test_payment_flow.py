"""HIH-9: сквозная проверка флоу заказа с оплатой (заказ → шлюз → возврат → статус).

БД — временный SQLite, шлюз — httpx.MockTransport, почта — перехватывается.
Реальной сети и реального Сбера здесь нет.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "back"))

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("EMAIL_ENABLED", "false")
os.environ.setdefault("BASE_URL", "https://hand-in-hand.ru")

import database            # noqa: E402
import mail                # noqa: E402
import main                # noqa: E402
import settings_store      # noqa: E402
from models import Order, Picture  # noqa: E402
from payments import sber  # noqa: E402


@pytest.fixture
def db():
    """Отдельная временная БД на тест; SessionLocal подменён везде."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite:///{path}"
    engine = database.create_engine(url, connect_args={"check_same_thread": False})
    TestSession = database.sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(engine)

    original = (database.engine, database.SessionLocal, main.SessionLocal)
    database.engine, database.SessionLocal, main.SessionLocal = engine, TestSession, TestSession
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        database.engine, database.SessionLocal, main.SessionLocal = original
        engine.dispose()
        os.unlink(path)


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """In-memory rate-лимитер /api/orders общий на процесс — обнуляем между тестами."""
    main.RATE_LIMITS.clear()
    yield
    main.RATE_LIMITS.clear()


@pytest.fixture
def client(db):
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def picture(db):
    p = Picture(image_path="/uploads/test.jpg", title="Тест", author="Автор", age=8,
                price=2500, min_price=500, status="available", history="история")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture
def gateway(monkeypatch):
    """Мок шлюза: очередь ответов + собранные тела запросов."""
    state = {"requests": [], "script": [], "bodies": []}

    def handler(request: httpx.Request) -> httpx.Response:
        state["requests"].append(request)
        if request.method == "GET":
            state["bodies"].append(dict(request.url.params))
        else:
            state["bodies"].append(dict(httpx.QueryParams(request.content.decode("utf-8"))))
        reply = state["script"].pop(0) if state["script"] else {"json": {"errorCode": "999",
                                                                        "errorMessage": "нет сценария"}}
        return httpx.Response(reply.get("status", 200), json=reply.get("json", {}))

    monkeypatch.setattr(sber, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(sber, "log_exchange", lambda **kw: None)
    monkeypatch.setenv("SBER_USER_NAME", "unit-user")
    monkeypatch.setenv("SBER_PASSWORD", "unit-secret")
    return state


def _order_payload(picture_id, price=1000, method="card", phone=""):
    return {"customer_name": "Покупатель", "customer_email": "buy@example.com",
            "customer_phone": phone, "payment_method": method,
            "items": [{"picture_id": picture_id, "offered_price": price}]}


# ─── режим «оплата выключена» — старая схема ─────────────────────────────────

def test_payments_off_keeps_legacy_flow(client, db, picture):
    r = client.post("/api/orders", json=_order_payload(picture.id, 1000))
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["payment_status"] == "paid"
    assert data["payment_url"] == ""
    db.refresh(picture)
    assert picture.status == "sold" and picture.order_id == data["order_id"]


def test_payments_off_keeps_failure_stub(client, db, picture):
    r = client.post("/api/orders", json=_order_payload(picture.id, 1000, phone="78889990002"))
    assert r.status_code == 402
    assert r.json()["payment_status"] == "failed"
    db.refresh(picture)
    assert picture.status == "available" and picture.order_id is None


# ─── режим «оплата включена» ─────────────────────────────────────────────────

def test_payments_on_creates_pending_and_returns_gateway_url(client, db, picture, gateway):
    settings_store.set_bool(db, "payments_enabled", True)
    gateway["script"].append({"json": {"orderId": "777", "formUrl": "https://pay.sber/form/777"}})

    r = client.post("/api/orders", json=_order_payload(picture.id, 2500, method="sberpay"))
    assert r.status_code == 201, r.text
    data = r.json()
    order = db.get(Order, data["order_id"])

    assert data["payment_status"] == "pending"
    assert data["payment_url"] == "https://pay.sber/form/777"
    assert order.sber_order_id == "777"
    # картина зарезервирована, но ещё не продана
    db.refresh(picture)
    assert picture.status == "available" and picture.order_id == order.id
    # в шлюз ушла сумма в копейках и обязательный блок SberPay
    body = gateway["bodies"][-1]
    assert body["amount"] == "250000"
    assert body["orderNumber"] == str(order.id)
    assert "sberbankOnlineAttributes" in body["jsonParams"]
    assert body["returnUrl"] == "https://hand-in-hand.ru/payment/return"


def test_return_confirms_payment_and_sends_letter(client, db, picture, gateway, monkeypatch):
    settings_store.set_bool(db, "payments_enabled", True)
    settings_store.set_bool(db, "email_after_purchase", True)
    sent = []
    monkeypatch.setattr(mail, "EMAIL_ENABLED", True)
    monkeypatch.setattr(mail, "send_email", lambda to, subject, html, items=None: sent.append(to))

    gateway["script"].append({"json": {"orderId": "11", "formUrl": "https://pay/form"}})
    order_id = client.post("/api/orders", json=_order_payload(picture.id, 1000)).json()["order_id"]
    assert sent == []                                   # до подтверждения письмо не уходит

    gateway["script"].append({"json": {"orderStatus": 2, "orderId": "11",
                                       "amount": 100000, "orderNumber": str(order_id)}})
    r = client.get(f"/payment/return?merchantOrderId={order_id}&orderId=11", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/?payment=success"

    order = db.get(Order, order_id)
    db.refresh(picture)
    assert order.payment_status == "paid" and order.email_status == "sent"
    assert picture.status == "sold" and picture.sold_at is not None
    assert sent == ["buy@example.com"]


def test_return_is_idempotent(client, db, picture, gateway):
    settings_store.set_bool(db, "payments_enabled", True)
    settings_store.set_bool(db, "email_after_purchase", False)
    gateway["script"].append({"json": {"orderId": "12", "formUrl": "https://pay/form"}})
    order_id = client.post("/api/orders", json=_order_payload(picture.id, 1000)).json()["order_id"]

    gateway["script"].append({"json": {"orderStatus": 2, "amount": 100000}})
    client.get(f"/payment/return?merchantOrderId={order_id}", follow_redirects=False)
    db.refresh(picture)
    first_sold_at = picture.sold_at
    assert db.get(Order, order_id).payment_status == "paid"

    # второй возврат не должен повторно дёргать шлюз и менять данные
    calls_before = len(gateway["requests"])
    r = client.get(f"/payment/return?merchantOrderId={order_id}", follow_redirects=False)
    assert r.headers["location"] == "/?payment=success"
    assert len(gateway["requests"]) == calls_before
    db.refresh(picture)
    assert picture.sold_at == first_sold_at


def test_return_with_wrong_amount_does_not_confirm(client, db, picture, gateway):
    settings_store.set_bool(db, "payments_enabled", True)
    gateway["script"].append({"json": {"orderId": "13", "formUrl": "https://pay/form"}})
    order_id = client.post("/api/orders", json=_order_payload(picture.id, 1000)).json()["order_id"]

    gateway["script"].append({"json": {"orderStatus": 2, "amount": 1, "orderNumber": str(order_id)}})
    r = client.get(f"/payment/return?merchantOrderId={order_id}", follow_redirects=False)
    assert r.headers["location"] == "/?payment=pending"

    order = db.get(Order, order_id)
    db.refresh(picture)
    assert order.payment_status == "pending"            # оплату не подтверждаем
    assert picture.status == "available"


def test_fail_url_releases_reservation(client, db, picture, gateway):
    settings_store.set_bool(db, "payments_enabled", True)
    gateway["script"].append({"json": {"orderId": "14", "formUrl": "https://pay/form"}})
    order_id = client.post("/api/orders", json=_order_payload(picture.id, 1000)).json()["order_id"]

    gateway["script"].append({"json": {"orderStatus": 3}})   # 3 = отказ
    r = client.get(f"/payment/fail?merchantOrderId={order_id}", follow_redirects=False)
    assert r.headers["location"] == "/?payment=failed"

    assert db.get(Order, order_id).payment_status == "failed"
    db.refresh(picture)
    assert picture.status == "available" and picture.order_id is None   # снова в продаже


def test_status_pending_keeps_reservation(client, db, picture, gateway):
    settings_store.set_bool(db, "payments_enabled", True)
    gateway["script"].append({"json": {"orderId": "15", "formUrl": "https://pay/form"}})
    order_id = client.post("/api/orders", json=_order_payload(picture.id, 1000)).json()["order_id"]

    gateway["script"].append({"json": {"orderStatus": 0}})
    r = client.get(f"/payment/return?merchantOrderId={order_id}", follow_redirects=False)
    assert r.headers["location"] == "/?payment=pending"
    db.refresh(picture)
    assert picture.order_id == order_id                 # ждём, резерв держим


def test_forged_query_params_cannot_pay(client, db, picture, gateway):
    """Никакие параметры из браузера не делают заказ оплаченным — решает только шлюз."""
    settings_store.set_bool(db, "payments_enabled", True)
    gateway["script"].append({"json": {"orderId": "16", "formUrl": "https://pay/form"}})
    order_id = client.post("/api/orders", json=_order_payload(picture.id, 1000)).json()["order_id"]

    gateway["script"].append({"json": {"orderStatus": 5}})   # шлюз говорит «отклонён»
    client.get(f"/payment/return?merchantOrderId={order_id}&orderStatus=2&status=paid&rnd=1",
               follow_redirects=False)
    assert db.get(Order, order_id).payment_status == "failed"


def test_unknown_order_redirects_without_change(client, db, picture, gateway):
    r = client.get("/payment/return?merchantOrderId=999999", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/?payment=unknown"


def test_gateway_registration_failure_fails_order(client, db, picture, gateway):
    settings_store.set_bool(db, "payments_enabled", True)
    gateway["script"].append({"json": {"errorCode": "101", "errorMessage": "Неверная учётка"}})
    r = client.post("/api/orders", json=_order_payload(picture.id, 1000))
    assert r.status_code == 502
    db.refresh(picture)
    assert picture.status == "available" and picture.order_id is None


def test_payments_on_without_credentials_returns_503(client, db, picture, monkeypatch):
    settings_store.set_value(db, "payments_enabled", "true")
    monkeypatch.delenv("SBER_USER_NAME", raising=False)
    monkeypatch.delenv("SBER_PASSWORD", raising=False)
    settings_store.set_value(db, "sber_user_name", "")
    settings_store.set_value(db, "sber_password", "")
    r = client.post("/api/orders", json=_order_payload(picture.id, 1000))
    assert r.status_code == 503
    assert "учётные данные" in r.json()["detail"]


def test_email_flag_off_skips_letter(client, db, picture, gateway, monkeypatch):
    settings_store.set_bool(db, "payments_enabled", True)
    settings_store.set_bool(db, "email_after_purchase", False)
    sent = []
    monkeypatch.setattr(mail, "EMAIL_ENABLED", True)
    monkeypatch.setattr(mail, "send_email", lambda to, subject, html, items=None: sent.append(to))

    gateway["script"].append({"json": {"orderId": "17", "formUrl": "https://pay/form"}})
    order_id = client.post("/api/orders", json=_order_payload(picture.id, 1000)).json()["order_id"]
    gateway["script"].append({"json": {"orderStatus": 2, "amount": 100000}})
    client.get(f"/payment/return?merchantOrderId={order_id}", follow_redirects=False)

    assert sent == []                                   # флаг выключен — письма нет
    assert db.get(Order, order_id).payment_status == "paid"
    assert db.get(Order, order_id).email_status == "not_sent"


def test_stale_pending_reservation_is_released(client, db, picture, gateway):
    """Покинул страницу банка → через час резерв снимается, картина снова продаётся."""
    settings_store.set_bool(db, "payments_enabled", True)
    gateway["script"].append({"json": {"orderId": "18", "formUrl": "https://pay/form"}})
    order_id = client.post("/api/orders", json=_order_payload(picture.id, 1000)).json()["order_id"]

    order = db.get(Order, order_id)
    order.created_at = datetime.now() - timedelta(minutes=120)
    db.commit()
    db.refresh(picture)
    assert picture.order_id == order_id                 # резерв висит

    client.get("/api/pictures")                         # ленивая чистка в списке витрины
    db.expire_all()
    db.refresh(picture)
    assert picture.order_id is None and picture.status == "available"
    assert db.get(Order, order_id).payment_status == "failed"
    assert db.get(Order, order_id).cancelled_at is not None
