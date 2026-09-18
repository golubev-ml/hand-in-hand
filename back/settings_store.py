"""HIH-9: настройки приложения в БД (таблица settings) с env-фолбэком.

Правило: значение берётся из БД (вводится в админке), если там пусто — из переменной
окружения, если и её нет — из DEFAULTS. Секретов в коде нет: здесь только имена
ключей и дефолты неверток.
"""
import os

from models import Setting

# Ключи настроек и дефолты. env — фолбэк, если в БД значение пустое.
DEFAULTS: dict[str, str] = {
    "payments_enabled": "false",       # оплата Сбербанком: по умолчанию ВЫКЛ
    "email_after_purchase": "true",    # письмо покупателю после paid: по умолчанию ВКЛ
    "sber_user_name": "",              # userName register.do
    "sber_merchant_login": "",         # merchantLogin (идентификатор мерчанта)
    "sber_terminal": "",               # номер терминала
    "sber_key_id": "",                 # ID ключа (подпись ответов шлюза)
    "sber_password": "",                # password для register.do/getOrderStatus.do
    "sber_key": "",                     # ключ мерчанта для подписи, отдельно от password
}

ENV_FALLBACK: dict[str, str] = {
    "payments_enabled": "SBER_PAYMENTS_ENABLED",
    "email_after_purchase": "EMAIL_AFTER_PURCHASE",
    "sber_user_name": "SBER_USER_NAME",
    "sber_merchant_login": "SBER_MERCHANT_LOGIN",
    "sber_terminal": "SBER_TERMINAL",
    "sber_key_id": "SBER_KEY_ID",
    "sber_password": "SBER_PASSWORD",
    "sber_key": "SBER_KEY",
}

TRUTHY = {"1", "true", "yes", "on", "вкл", "да"}

# Секретные ключи: их нельзя показывать в админке целиком и нельзя писать в лог.
SECRET_KEYS = {"sber_password", "sber_key"}


def known_keys() -> list[str]:
    return list(DEFAULTS)


def get_value(db, key: str, default: str | None = None) -> str:
    """Строгое значение: БД → env → DEFAULTS. db=None — только env/дефолт (для тестов)."""
    value = ""
    if db is not None:
        row = db.get(Setting, key)
        if row is not None and row.value is not None:
            value = row.value
    if not value:
        env_name = ENV_FALLBACK.get(key)
        if env_name:
            value = os.getenv(env_name, "")
    if not value:
        value = default if default is not None else DEFAULTS.get(key, "")
    return value


def set_value(db, key: str, value: str, updated_by: str = "") -> None:
    """Сохраняет настройку (upsert) и коммитит."""
    row = db.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value, updated_by=updated_by)
        db.add(row)
    else:
        row.value = value
        row.updated_by = updated_by
    db.commit()


def get_bool(db, key: str) -> bool:
    return get_value(db, key).strip().lower() in TRUTHY


def set_bool(db, key: str, enabled: bool, updated_by: str = "") -> None:
    set_value(db, key, "true" if enabled else "false", updated_by)


def mask(value: str) -> str:
    """Маска секрета для отображения в админке: видно только последние 4 символа."""
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


def payments_enabled(db) -> bool:
    return get_bool(db, "payments_enabled")


def email_after_purchase(db) -> bool:
    return get_bool(db, "email_after_purchase")


def credentials(db) -> dict:
    """Учётные данные шлюза для payments/sber.py (секреты — только здесь и в логах masked)."""
    return {
        "user_name": get_value(db, "sber_user_name"),
        "merchant_login": get_value(db, "sber_merchant_login"),
        "terminal": get_value(db, "sber_terminal"),
        "key_id": get_value(db, "sber_key_id"),
        "password": get_value(db, "sber_password"),
    }


def is_configured(db) -> bool:
    creds = credentials(db)
    return bool(creds["user_name"] and creds["password"])
