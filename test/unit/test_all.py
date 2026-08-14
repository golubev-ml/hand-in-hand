"""Юнит-тесты: auth, rate-limiter, pydantic-schemas.
Тестируем чистую логику без БД/сети."""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

# sys.path уже настроен в conftest.py
import auth
import schemas


# =====================================================================
# 1. auth.hash_password + verify_password
# =====================================================================

class TestPasswordHashing:
    """~25 тестов: хэширование и проверка паролей."""

    @pytest.mark.parametrize("password", [
        "simple",
        "short",
        "longpassword123",
        "WithSpecialChars!@#$%",
        "UnicodeПарольКириллица",
        "with spaces inside",
        "   leadingtrailing   ",
        "123456",
        "qwerty",
        "P@$$w0rd!",
        "verylongpassword" * 5,  # >72 байт — bcrypt обрезает
        "",  # пустой пароль
        "a",
        "z",
        "A",
        "Z",
    ])
    def test_hash_and_verify(self, password):
        hashed = auth.hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password  # хэш отличается от пароля
        assert auth.verify_password(password, hashed)

    @pytest.mark.parametrize("password,wrong", [
        ("secret", "wrong"),
        ("hello", "HELLO"),  # регистр важен
        ("pass", "pass1"),
        ("123", "1234"),
        (" ", ""),
    ])
    def test_verify_wrong_password(self, password, wrong):
        hashed = auth.hash_password(password)
        assert not auth.verify_password(wrong, hashed)

    def test_different_passwords_different_hashes(self):
        h1 = auth.hash_password("password1")
        h2 = auth.hash_password("password2")
        assert h1 != h2

    def test_same_password_different_hashes(self):
        """bcrypt генерирует случайную соль — хэши одного пароля разные."""
        h1 = auth.hash_password("same")
        h2 = auth.hash_password("same")
        assert h1 != h2
        # Но оба проходят проверку
        assert auth.verify_password("same", h1)
        assert auth.verify_password("same", h2)


# =====================================================================
# 2. auth.create_token — JWT
# =====================================================================

class TestCreateToken:
    """~15 тестов: создание JWT."""

    @pytest.mark.parametrize("manager_id,login", [
        (1, "admin"),
        (42, "manager"),
        (999, "user_long_login_name"),
        (1, "a"),
    ])
    def test_token_structure(self, manager_id, login):
        import jwt
        token = auth.create_token(manager_id, login)
        assert isinstance(token, str)
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert payload["sub"] == str(manager_id)
        assert payload["login"] == login
        assert "exp" in payload

    def test_token_expires_in_12_hours(self):
        import jwt
        before = datetime.now(timezone.utc)
        token = auth.create_token(1, "admin")
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        # exp ≈ now + 12 часов (±1 минута)
        expected = before + timedelta(hours=auth.TOKEN_HOURS)
        assert abs((exp - expected).total_seconds()) < 60

    def test_token_algorithm_hs256(self):
        assert auth.ALGORITHM == "HS256"

    def test_token_hours_constant(self):
        assert auth.TOKEN_HOURS == 12


# =====================================================================
# 3. Schemas валидация
# =====================================================================

class TestManagerCreateSchema:
    """~8 тестов."""

    def test_valid(self):
        m = schemas.ManagerCreate(login="admin", password="secret123")
        assert m.login == "admin"

    @pytest.mark.parametrize("login", ["", "ab"])  # слишком короткий
    def test_login_too_short(self, login):
        with pytest.raises(ValueError):
            schemas.ManagerCreate(login=login, password="secret123")

    def test_login_too_long(self):
        with pytest.raises(ValueError):
            schemas.ManagerCreate(login="a" * 51, password="secret123")

    @pytest.mark.parametrize("password", ["", "12345"])  # слишком короткий
    def test_password_too_short(self, password):
        with pytest.raises(ValueError):
            schemas.ManagerCreate(login="admin", password=password)

    def test_password_too_long(self):
        with pytest.raises(ValueError):
            schemas.ManagerCreate(login="admin", password="x" * 101)


class TestPictureCreateSchema:
    """~8 тестов."""

    def test_minimal_valid(self):
        p = schemas.PictureCreate(image_path="/path.jpg")
        assert p.image_path == "/path.jpg"
        assert p.price == 0.0
        assert p.status == "available"

    @pytest.mark.parametrize("price", [-1, -100, -0.01])
    def test_price_negative(self, price):
        with pytest.raises(ValueError):
            schemas.PictureCreate(image_path="/p.jpg", price=price)

    def test_price_zero_ok(self):
        p = schemas.PictureCreate(image_path="/p.jpg", price=0)
        assert p.price == 0.0

    def test_price_positive(self):
        p = schemas.PictureCreate(image_path="/p.jpg", price=100.5)
        assert p.price == 100.5

    def test_all_fields(self):
        p = schemas.PictureCreate(
            image_path="/p.jpg", title="t", author="a", age=10,
            category="digital", description="d", history="h",
            price=50, status="available", is_new=True,
            is_featured=True, popularity=5,
        )
        assert p.title == "t"
        assert p.is_new is True


class TestOrderCreateSchema:
    """~8 тестов."""

    def test_minimal_valid(self):
        o = schemas.OrderCreate(
            name="Ivan", email="ivan@test.com",
            items=[schemas.OrderItem(title="pic", img="/i.jpg")],
        )
        assert o.name == "Ivan"

    def test_empty_name(self):
        with pytest.raises(ValueError):
            schemas.OrderCreate(name="", email="a@b.c",
                                items=[schemas.OrderItem(title="t", img="i")])

    def test_name_too_long(self):
        with pytest.raises(ValueError):
            schemas.OrderCreate(name="x" * 101, email="a@b.c",
                                items=[schemas.OrderItem(title="t", img="i")])

    def test_empty_email(self):
        with pytest.raises(ValueError):
            schemas.OrderCreate(name="N", email="",
                                items=[schemas.OrderItem(title="t", img="i")])

    def test_email_too_long(self):
        with pytest.raises(ValueError):
            schemas.OrderCreate(name="N", email="a" * 255 + "@b.c",
                                items=[schemas.OrderItem(title="t", img="i")])

    def test_empty_items(self):
        with pytest.raises(ValueError):
            schemas.OrderCreate(name="N", email="a@b.c", items=[])

    def test_item_negative_price(self):
        with pytest.raises(ValueError):
            schemas.OrderCreate(
                name="N", email="a@b.c",
                items=[schemas.OrderItem(title="t", img="i", price=-1)],
            )

    def test_item_zero_qty(self):
        with pytest.raises(ValueError):
            schemas.OrderCreate(
                name="N", email="a@b.c",
                items=[schemas.OrderItem(title="t", img="i", qty=0)],
            )


class TestPictureOrderCreateSchema:
    """~8 тестов."""

    def test_valid(self):
        p = schemas.PictureOrderCreate(
            customer_name="Ivan", customer_email="i@t.com",
            customer_phone="123", picture_ids=[1],
        )
        assert p.customer_phone == "123"

    def test_empty_name(self):
        with pytest.raises(ValueError):
            schemas.PictureOrderCreate(
                customer_name="", customer_email="i@t.com",
                customer_phone="123", picture_ids=[1],
            )

    def test_empty_email(self):
        with pytest.raises(ValueError):
            schemas.PictureOrderCreate(
                customer_name="Ivan", customer_email="",
                customer_phone="123", picture_ids=[1],
            )

    def test_empty_phone(self):
        with pytest.raises(ValueError):
            schemas.PictureOrderCreate(
                customer_name="Ivan", customer_email="i@t.com",
                customer_phone="", picture_ids=[1],
            )

    def test_phone_too_long(self):
        with pytest.raises(ValueError):
            schemas.PictureOrderCreate(
                customer_name="Ivan", customer_email="i@t.com",
                customer_phone="1" * 21, picture_ids=[1],
            )

    def test_empty_picture_ids(self):
        with pytest.raises(ValueError):
            schemas.PictureOrderCreate(
                customer_name="Ivan", customer_email="i@t.com",
                customer_phone="123", picture_ids=[],
            )


class TestDonationCreateSchema:
    """~8 тестов."""

    def test_valid(self):
        d = schemas.DonationCreate(name="Ivan", card="123456789012", price=100)
        assert d.price == 100

    def test_empty_name(self):
        with pytest.raises(ValueError):
            schemas.DonationCreate(name="", card="123456789012", price=100)

    @pytest.mark.parametrize("card", ["12345678901", ""])  # слишком короткий
    def test_card_too_short(self, card):
        with pytest.raises(ValueError):
            schemas.DonationCreate(name="N", card=card, price=100)

    def test_card_too_long(self):
        with pytest.raises(ValueError):
            schemas.DonationCreate(name="N", card="1" * 26, price=100)

    @pytest.mark.parametrize("price", [0, -1, -100])
    def test_price_not_positive(self, price):
        with pytest.raises(ValueError):
            schemas.DonationCreate(name="N", card="123456789012", price=price)


class TestManagerStatusUpdateSchema:
    """~2 теста."""

    @pytest.mark.parametrize("status", ["active", "blocked"])
    def test_valid(self, status):
        s = schemas.ManagerStatusUpdate(status=status)
        assert s.status == status


class TestDonationStatusUpdateSchema:
    """~3 теста."""

    @pytest.mark.parametrize("status", ["pending", "confirmed", "rejected"])
    def test_valid(self, status):
        s = schemas.DonationStatusUpdate(status=status)
        assert s.status == status


# =====================================================================
# 4. Rate limiter
# =====================================================================

class TestRateLimiter:
    """~15 тестов."""

    @pytest.fixture(autouse=True)
    def reset_rate_limits(self):
        """Сбрасываем словарь перед каждым тестом."""
        from main import RATE_LIMITS
        RATE_LIMITS.clear()
        yield
        RATE_LIMITS.clear()

    def test_first_request_allowed(self):
        from main import _check_rate_limit
        assert _check_rate_limit("1.2.3.4", "/api/orders")

    def test_requests_under_limit(self, monkeypatch):
        from main import RATE_LIMIT_REQUESTS
        from main import _check_rate_limit
        for i in range(RATE_LIMIT_REQUESTS - 1):
            assert _check_rate_limit("1.2.3.4", "/api/orders")

    def test_limit_exceeded(self, monkeypatch):
        from main import RATE_LIMIT_REQUESTS
        from main import _check_rate_limit
        for _ in range(RATE_LIMIT_REQUESTS):
            _check_rate_limit("1.2.3.4", "/api/orders")
        assert not _check_rate_limit("1.2.3.4", "/api/orders")

    def test_different_ips_independent(self, monkeypatch):
        from main import RATE_LIMIT_REQUESTS
        from main import _check_rate_limit
        for _ in range(RATE_LIMIT_REQUESTS):
            _check_rate_limit("1.2.3.4", "/api/orders")
        # другой IP не заблокирован
        assert _check_rate_limit("5.6.7.8", "/api/orders")

    def test_different_paths_independent(self, monkeypatch):
        from main import RATE_LIMIT_REQUESTS
        from main import _check_rate_limit
        for _ in range(RATE_LIMIT_REQUESTS):
            _check_rate_limit("1.2.3.4", "/api/orders")
        assert _check_rate_limit("1.2.3.4", "/admin/login")

    def test_window_expires(self, monkeypatch):
        """После истечения окна — лимит сбрасывается."""
        from main import _check_rate_limit, RATE_LIMITS, RATE_LIMIT_REQUESTS
        import main as m
        original_window = m.RATE_LIMIT_WINDOW_SECONDS
        m.RATE_LIMIT_WINDOW_SECONDS = 1
        try:
            for _ in range(RATE_LIMIT_REQUESTS):
                _check_rate_limit("1.2.3.4", "/api/orders")
            assert not _check_rate_limit("1.2.3.4", "/api/orders")
            time.sleep(1.1)
            assert _check_rate_limit("1.2.3.4", "/api/orders")
        finally:
            m.RATE_LIMIT_WINDOW_SECONDS = original_window


# =====================================================================
# 5. JWT безопасность
# =====================================================================

class TestJWTSecurity:
    """~10 тестов."""

    def test_expired_token(self):
        import jwt
        payload = {
            "sub": "1", "login": "admin",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])

    def test_wrong_secret(self):
        import jwt
        token = auth.create_token(1, "admin")
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=[auth.ALGORITHM])

    def test_algorithm_none_rejected(self):
        import jwt
        payload = {"sub": "1", "login": "admin",
                   "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, "", algorithm="none")
        with pytest.raises(jwt.InvalidAlgorithmError):
            jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])

    def test_tampered_token(self):
        import jwt
        token = auth.create_token(1, "admin")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(Exception):
            jwt.decode(tampered, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])

    def test_missing_sub(self):
        import jwt
        payload = {"login": "admin",
                   "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
        p = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert "sub" not in p

    def test_missing_exp_rejected(self):
        import jwt
        payload = {"sub": "1", "login": "admin"}
        token = jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)
        with pytest.raises(Exception):
            jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM],
                       options={"require": ["exp"]})
EOF