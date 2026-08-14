import os
import httpx
import pytest

API = os.getenv("API_URL", "http://api:8000")
MAILHOG = os.getenv("MAILHOG_URL", "http://mailhog:8025")
PHONE_OK = "78889990001"
PHONE_FAIL = "78889990002"


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=API, timeout=15) as c:
        yield c


def _order_payload(phone, pic_id):
    return {"customer_name": "Test", "customer_email": "test@example.com",
            "customer_phone": phone, "picture_ids": [pic_id]}


def _available(client, exclude=()):
    for p in client.get("/api/pictures").json():
        if p["id"] not in exclude and p.get("status", "available") == "available":
            return p
    raise AssertionError("не осталось доступных картин")


def test_01_pictures_list(client):
    r = client.get("/api/pictures")
    assert r.status_code == 200
    assert isinstance(r.json(), list) and len(r.json()) >= 1


def test_02_migration_pictures_present(client):
    assert len(client.get("/api/pictures").json()) >= 8


def test_03_order_paid_and_email(client):
    p = _available(client)
    r = client.post("/api/orders", json=_order_payload(PHONE_OK, p["id"]))
    assert r.status_code == 200, r.text
    assert r.json()["payment_status"] == "paid"
    assert r.json()["email_status"] == "sent"
    m = httpx.get(f"{MAILHOG}/api/v2/messages", timeout=10).json()
    assert m["total"] >= 1


def test_04_order_failed_phone(client):
    p = _available(client)
    r = client.post("/api/orders", json=_order_payload(PHONE_FAIL, p["id"]))
    assert r.status_code == 402
    assert r.json()["payment_status"] == "failed"


def test_05_sold_cannot_reorder(client):
    p = _available(client)
    ok = client.post("/api/orders", json=_order_payload(PHONE_OK, p["id"]))
    assert ok.status_code == 200
    again = client.post("/api/orders", json=_order_payload(PHONE_OK, p["id"]))
    assert again.status_code in (400, 409)


def test_06_total_from_server(client):
    p = _available(client)
    r = client.post("/api/orders", json=_order_payload(PHONE_OK, p["id"]))
    assert r.json()["total"] == pytest.approx(float(p["price"]))


def test_07_admin_requires_auth(client):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code in (302, 303, 307, 401, 403)


def test_08_admin_login_wrong_password(client):
    r = client.post("/admin/login", data={"login": "hand_admin", "password": "nope"},
                    follow_redirects=False)
    assert r.status_code in (200, 302, 303, 401, 403)
    r2 = client.get("/admin", follow_redirects=False)
    assert r2.status_code in (302, 303, 307, 401, 403)


def test_09_admin_login_ok_and_orders(client):
    s = httpx.Client(base_url=API, timeout=15)
    r = s.post("/admin/login",
               data={"login": os.environ["ADMIN_LOGIN"],
                     "password": os.environ["ADMIN_PASSWORD"]},
               follow_redirects=False)
    assert r.status_code in (200, 302, 303)
    r2 = s.get("/admin/orders")
    assert r2.status_code == 200 and "Test" in r2.text


def test_10_rate_limit_orders():
    c = httpx.Client(base_url="http://api:8000", timeout=15)
    codes = [c.post("/api/orders",
                    json=_order_payload(PHONE_OK, 999999)).status_code
             for _ in range(40)]
    assert 429 in codes
