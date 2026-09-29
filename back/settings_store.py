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

# Допустимые вторые имена. В документации Сбера и в чужих .env часто встречаются
# SBER_USERNAME / SBER_API_URL — если читать только «наши» имена, такая строка в
# .env молча игнорируется, и на бой уезжает пустой или тестовый userName.
ENV_ALIASES: dict[str, tuple[str, ...]] = {
    "sber_user_name": ("SBER_USERNAME",),
    "sber_password": ("SBER_MERCHANT_PASSWORD",),
}

TRUTHY = {"1", "true", "yes", "on", "вкл", "да"}

# Секретные ключи: их нельзя показывать в админке целиком и нельзя писать в лог.
SECRET_KEYS = {"sber_password", "sber_key"}


def known_keys() -> list[str]:
    return list(DEFAULTS)


def _env_value(key: str) -> tuple[str, str]:
    """(значение, имя переменной), откуда оно взято; каноническое имя приоритетнее."""
    names = [ENV_FALLBACK.get(key)] if ENV_FALLBACK.get(key) else []
    names += list(ENV_ALIASES.get(key, ()))
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value, name
    return "", ""


def resolve(db, key: str) -> tuple[str, str]:
    """Значение + человекочитаемый источник («БД (админка)», «env SBER_X», «по умолчанию»).

    Источник нужен для диагностики: когда в БД лежат тестовые ключи, а на сервере
    прописан боевой env, значение из env молча не применяется — без источника это
    выглядит как «пароль не подходит».
    """
    if db is not None:
        row = db.get(Setting, key)
        if row is not None and (row.value or "").strip():
            return row.value, "БД (админка)"
    value, name = _env_value(key)
    if value:
        canonical = ENV_FALLBACK.get(key)
        suffix = "" if name == canonical else " — алиас, ожидалось " + (canonical or "другое имя")
        return value, f"env {name}{suffix}"
    return DEFAULTS.get(key, ""), "по умолчанию"


def get_value(db, key: str, default: str | None = None) -> str:
    """Строгое значение: БД → env (включая алиасы) → DEFAULTS. db=None — только env."""
    value, _source = resolve(db, key)
    if not value and default is not None:
        return default
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


def sources(db) -> dict:
    """Откуда берётся каждая настройка — для админки и для логов (без значений)."""
    return {key: resolve(db, key)[1] for key in DEFAULTS}


def warnings(db) -> list[str]:
    """Что выглядит подозрительно в конфигурации. Значения секретов не возвращаются."""
    notes: list[str] = []

    if get_bool(db, "payments_enabled") and not is_configured(db):
        notes.append("Оплата включена, но userName или password не заданы — заказ не сможет уйти в шлюз.")

    for key in ("sber_user_name", "sber_password"):
        db_value, _ = resolve(db, key)
        env_value, env_name = _env_value(key)
        if db_value and env_value and db_value != env_value:
            notes.append(
                f"{key}: в БД и в env ({env_name}) лежат РАЗНЫЕ значения — работает то, что в БД. "
                "Если на сервере поменяли env, а в БД остались тестовые ключи, бой ходит с тестовой учёткой."
            )
        value = db_value or env_value
        if value and "$" in value:
            notes.append(
                f"{key}: значение содержит «$» — docker compose подставляет переменные и внутри .env, "
                "поэтому пароль мог обрезаться. Экранируйте «$» как «$$» или задавайте его через админку."
            )

    _value, name = _env_value("sber_user_name")
    canonical = ENV_FALLBACK.get("sber_user_name")
    if name and name != canonical:
        notes.append(f"userName читается из {name}; штатное имя переменной — {canonical}.")
    return notes


def is_configured(db) -> bool:
    creds = credentials(db)
    return bool(creds["user_name"] and creds["password"])
