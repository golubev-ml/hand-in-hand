"""HIH-9: раздел /admin/settings — рендер, сохранение флагов, маскирование секрета."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "back"))

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("ADMIN_LOGIN", "settings_tester")
os.environ.setdefault("ADMIN_PASSWORD", "secret-of-this-test")

import database           # noqa: E402
import main               # noqa: E402
import settings_store     # noqa: E402
from auth import hash_password  # noqa: E402
from models import Manager  # noqa: E402

ADMIN = ("settings_tester", "secret-of-this-test")


@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = database.create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    TestSession = database.sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(engine)
    original = (database.engine, database.SessionLocal, main.SessionLocal)
    database.engine, database.SessionLocal, main.SessionLocal = engine, TestSession, TestSession

    # Администратора заводим сами: main читает ADMIN_LOGIN/ADMIN_PASSWORD один раз при
    # импорте, а порядок импорта тестовых модулей в pytest может быть любым.
    bootstrap = TestSession()
    bootstrap.add(Manager(login=ADMIN[0], password_hash=hash_password(ADMIN[1]), status="active"))
    bootstrap.commit()
    bootstrap.close()

    monkeypatch.setattr(main, "ADMIN_LOGIN", ADMIN[0])
    monkeypatch.setattr(main, "ADMIN_PASSWORD", ADMIN[1])
    # cookie админки получает флаг Secure, когда BASE_URL https (см. admin_panel.do_login);
    # тестовый транспорт — http, поэтому фиксируем http, независимо от порядка импорта модулей
    monkeypatch.setenv("BASE_URL", "http://testserver")
    main.RATE_LIMITS.clear()
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        login = c.post("/admin/login", data={"login": ADMIN[0], "password": ADMIN[1]},
                       follow_redirects=False)
        assert login.status_code == 302, f"не удалось войти в админку: {login.status_code}"
        yield c
    main.RATE_LIMITS.clear()
    database.engine, database.SessionLocal, main.SessionLocal = original
    engine.dispose()
    os.unlink(path)


def test_settings_page_shows_flags_off_by_default(client):
    r = client.get("/admin/settings")
    assert r.status_code == 200
    body = r.text
    assert "Оплата включена" in body and "Отправлять письмо после покупки" in body
    assert "выключена" in body                      # оплата по умолчанию ВЫКЛ
    assert 'name="payments_enabled"' in body and 'name="email_after_purchase"' in body
    assert 'name="sber_key" type="password"' in body


def test_flags_saved_and_read_back(client):
    r = client.post("/admin/settings", data={
        "payments_enabled": "on", "email_after_purchase": "on",
        "sber_user_name": "term-user", "sber_merchant_login": "merchant-1",
        "sber_terminal": "22", "sber_key_id": "kid-9", "sber_key": "super-secret-value",
    }, follow_redirects=False)
    assert r.status_code == 302

    db = database.SessionLocal()
    try:
        assert settings_store.get_bool(db, "payments_enabled") is True
        assert settings_store.get_bool(db, "email_after_purchase") is True
        assert settings_store.get_value(db, "sber_user_name") == "term-user"
        assert settings_store.get_value(db, "sber_key") == "super-secret-value"
    finally:
        db.close()

    body = client.get("/admin/settings").text
    assert "value=\"term-user\"" in body
    assert "super-secret-value" not in body          # секрет не отдаётся в HTML
    assert settings_store.mask("super-secret-value") in body   # только маска


def test_unchecked_payments_turns_off(client):
    client.post("/admin/settings", data={"payments_enabled": "on", "email_after_purchase": "on",
                                         "sber_user_name": "", "sber_merchant_login": "",
                                         "sber_terminal": "", "sber_key_id": "", "sber_key": ""})
    client.post("/admin/settings", data={"email_after_purchase": "on",
                                         "sber_user_name": "", "sber_merchant_login": "",
                                         "sber_terminal": "", "sber_key_id": "", "sber_key": ""})
    db = database.SessionLocal()
    try:
        assert settings_store.get_bool(db, "payments_enabled") is False
        assert settings_store.get_bool(db, "email_after_purchase") is True
    finally:
        db.close()


def test_empty_key_keeps_saved_secret(client):
    client.post("/admin/settings", data={"payments_enabled": "on", "email_after_purchase": "on",
                                         "sber_user_name": "u", "sber_merchant_login": "",
                                         "sber_terminal": "", "sber_key_id": "",
                                         "sber_key": "keep-me-123"})
    client.post("/admin/settings", data={"payments_enabled": "on", "email_after_purchase": "on",
                                         "sber_user_name": "u", "sber_merchant_login": "",
                                         "sber_terminal": "", "sber_key_id": "", "sber_key": ""})
    db = database.SessionLocal()
    try:
        assert settings_store.get_value(db, "sber_key") == "keep-me-123"
    finally:
        db.close()


def test_settings_requires_login(client):
    client.cookies.clear()
    r = client.get("/admin/settings", follow_redirects=False)
    assert r.status_code in (302, 303, 401)


def test_other_admin_sections_still_render(client):
    for path in ("/admin/", "/admin/pictures", "/admin/orders", "/admin/donations",
                 "/admin/contacts", "/admin/logs"):
        r = client.get(path)
        assert r.status_code == 200, f"{path} → {r.status_code}"
