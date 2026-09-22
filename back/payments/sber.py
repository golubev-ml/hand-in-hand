"""HIH-9: адаптер универсального платёжного шлюза Сбербанка (SberBank ecomm).

Контур по умолчанию — тестовый:  https://ecomtest.sberbank.ru/ecomm/gw/partner/api/v1/
Боевой:                            https://epay.sberbank.ru/ecomm/gw/partner/api/v1/
Переключается одной переменной SBER_BASE_URL (она же подменяется моком в тестах).

Соглашения, заложенные в ТЗ и здесь:
  * сумма в register.do — в КОПЕЙКАХ, orderNumber = внутренний id заказа;
  * статус оплаты решает ТОЛЬКО getOrderStatus.do, а не данные из браузера;
  * учётные данные берутся из таблицы settings (админка), env — только фолбэк;
  * каждый запрос/ответ шлюза уходит в таблицу Log, секреты маскируются.

Перед боевым включением флага «Оплата включена» подтвердить с инженером интеграции
Сбера (каркас правильный, правки — несколько строк/значений env):
  1. точные имена атрибутов способов оплаты в jsonParams — переопределяются через
     SBER_METHOD_ATTRS_JSON без правки кода;
  2. куда кладётся номер терминала (sber_terminal сейчас только хранится и
     показывается в админке, в шлюз не отправляется);
   3. нужен ли контроль подписи ответов по «key ID» + ключу (sber_key_id хранится,
      подпись сейчас не проверяется: статус заказа решается только по
      getOrderStatus.do на сервере, поэтому подпись браузера не влияет на оплату).
"""
import json
import os
import re
import ssl
import time
from pathlib import Path

import certifi
import httpx

import settings_store

TEST_BASE_URL = "https://ecomtest.sberbank.ru/ecomm/gw/partner/api/v1/"
PROD_BASE_URL = "https://epay.sberbank.ru/ecomm/gw/partner/api/v1/"
RUSSIAN_TRUSTED_ROOT_CA = Path(__file__).resolve().parents[1] / "certs" / "russian_trusted_root_ca.pem"

CURRENCY_RUB = 643
TIMEOUT_SECONDS = float(os.getenv("SBER_TIMEOUT_SECONDS", "15"))
RETRIES = int(os.getenv("SBER_RETRIES", "3"))


def verify_ssl() -> bool:
    """TLS verification may be disabled only for Sber's test contour."""
    raw = os.getenv("SBER_VERIFY_SSL", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}

# Способы оплаты, которые умеем регистрировать (WEB-канал).
METHODS = ("card", "sbp", "sberpay", "mirpay")

# Атрибуты register.do по способам оплаты. Для SberPay блок
# jsonParams.sberbankOnlineAttributes ОБЯЗАТЕЛЕН по требованиям шлюза.
DEFAULT_METHOD_ATTRS = {
    "card": {},
    "sbp": {"jsonParams": {"sbpAttributes": {"sbp.enabled": "true"}}},
    "mirpay": {"jsonParams": {"mirPayAttributes": {"mirpay.enabled": "true"}}},
    "sberpay": {"jsonParams": {"sberbankOnlineAttributes": {"sberpay.enabled": "true"}}},
}

# Поля, которые никогда не должны попасть в лог или ответ наружу.
SECRET_FIELD = re.compile(r"(password|secret|token|authorization|key)", re.I)

# Точка подмены транспорта в тестах: sber._transport = httpx.MockTransport(handler)
_transport = None


class SberError(Exception):
    """Ошибка шлюза или транспорта. endpoint/code — для разбора вызывающим кодом."""

    def __init__(self, message, code=None, endpoint=None, status=None):
        super().__init__(message)
        self.code = code
        self.endpoint = endpoint
        self.status = status


# ─── конфигурация и учётные данные ────────────────────────────────────────────

def base_url() -> str:
    """Базовый URL шлюза. env SBER_BASE_URL (для мока/продa), иначе тестовый контур."""
    return (os.getenv("SBER_BASE_URL") or TEST_BASE_URL).strip()


def credentials(db=None) -> dict:
    return settings_store.credentials(db)


def is_configured(db=None) -> bool:
    return settings_store.is_configured(db)


def method_attributes(method: str) -> dict:
    """Атрибуты способа оплаты; переопределяются env SBER_METHOD_ATTRS_JSON без релиза."""
    table = dict(DEFAULT_METHOD_ATTRS)
    raw = os.getenv("SBER_METHOD_ATTRS_JSON")
    if raw:
        try:
            for key, value in json.loads(raw).items():
                table[key] = value
        except (ValueError, AttributeError):
            pass  # не разобрали — работаем на дефолтах
    attrs = dict(table.get(method) or {})
    if method == "sberpay" and "jsonParams" not in attrs:
        # страховка от пустого переопределения: обязательный блок не должен пропасть
        attrs = dict(DEFAULT_METHOD_ATTRS["sberpay"])
    return attrs


# ─── маскирование и логирование ───────────────────────────────────────────────

def redact(value):
    """Рекурсивно заменяет секретные поля на *** — для Лога и любых ответов наружу."""
    if isinstance(value, dict):
        return {k: ("***" if SECRET_FIELD.search(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def dump_for_log(payload) -> str:
    return json.dumps(redact(payload), ensure_ascii=False, default=str)[:2000]


def log_exchange(text: str, url: str, request: str, response: str) -> None:
    """Пишет обмен с шлюзом в таблицу Log. Не бросает исключений — лог не должен ронять оплату."""
    try:
        from database import SessionLocal
        from models import Log

        db = SessionLocal()
        try:
            db.add(Log(text=text[:500], url=url[:500], request=request, response=response))
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 — только в stdout, секретов тут нет
        print(f">>> sber: не удалось записать в Log: {exc}")


# ─── транспорт ────────────────────────────────────────────────────────────────

def _client() -> httpx.Client:
    if _transport is not None:
        return httpx.Client(transport=_transport, timeout=TIMEOUT_SECONDS)
    if not verify_ssl():
        return httpx.Client(timeout=TIMEOUT_SECONDS, verify=False)
    context = ssl.create_default_context(cafile=certifi.where())
    if RUSSIAN_TRUSTED_ROOT_CA.exists():
        context.load_verify_locations(cafile=RUSSIAN_TRUSTED_ROOT_CA)
    return httpx.Client(timeout=TIMEOUT_SECONDS, verify=context)


def _decode(data: bytes, endpoint: str):
    if not data:
        return {}
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {
            "errorCode": "PARSE",
            "errorMessage": f"{endpoint}: ответ не JSON",
            "_raw": data[:400].decode("utf-8", errors="ignore"),
        }


def _request(client, http_method: str, url: str, body: dict, endpoint: str, no_retry: bool):
    """GET/POST с ретраями только на безопасные сбои (сеть/5xx/408/429)."""
    attempts = 0
    while True:
        try:
            if http_method == "GET":
                resp = client.get(url, params=body)
            else:
                resp = client.post(url, json=body)
        except httpx.RequestError as exc:
            if not no_retry and attempts < RETRIES:
                attempts += 1
                time.sleep(min(0.5 * 2 ** attempts, 4))
                continue
            raise SberError(f"{endpoint}: сетевая ошибка {type(exc).__name__}", endpoint=endpoint) from exc

        if resp.status_code in (408, 429) or resp.status_code >= 500:
            if not no_retry and attempts < RETRIES:
                attempts += 1
                time.sleep(min(0.5 * 2 ** attempts, 4))
                continue
            raise SberError(
                f"{endpoint}: HTTP {resp.status_code}",
                endpoint=endpoint, status=resp.status_code,
            )
        return resp


def call(endpoint: str, payload: dict, db=None, http_method: str = "POST", no_retry: bool = False) -> dict:
    """Единственная точка выхода наружу: подставляет учётку, логирует с маскированием."""
    creds = credentials(db)
    body = {"userName": creds["user_name"], "password": creds["password"]}
    body.update(payload)

    url = f"{base_url()}{endpoint}"
    safe_request = dump_for_log(body)
    started = time.monotonic()

    with _client() as client:
        resp = _request(client, http_method, url, body, endpoint, no_retry)

    data = _decode(resp.content, endpoint)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    log_exchange(
        text=f"SBER {endpoint} → HTTP {resp.status_code} ({elapsed_ms} мс)",
        url=url,
        request=safe_request,
        response=dump_for_log(data),
    )
    return data


def biz_error(data: dict, endpoint: str):
    """errorCode шлюза: «нет ошибки» = отсутствует|null|''|'0' (Сбер присылает его по-разному)."""
    code = data.get("errorCode")
    if code in (None, "", 0, "0"):
        return None
    return {"code": str(code), "message": str(data.get("errorMessage") or f"{endpoint}: errorCode {code}")}


# ─── методы API ───────────────────────────────────────────────────────────────

def to_kopecks(amount_rub) -> int:
    try:
        kop = int(round(float(amount_rub) * 100))
    except (TypeError, ValueError):
        raise SberError(f"Некорректная сумма: {amount_rub!r}") from None
    if kop <= 0:
        raise SberError("Сумма заказа должна быть больше нуля")
    return kop


def create_payment(order_number, amount_rub, method: str = "card", db=None,
                   return_url: str | None = None, fail_url: str | None = None,
                   description: str = "") -> dict:
    """register.do: регистрирует платёж, возвращает order_id шлюза и url платёжной формы."""
    if str(method).lower() not in METHODS:
        raise SberError(f"Неизвестный способ оплаты: {method}")
    order_number = str(order_number)
    if not order_number:
        raise SberError("orderNumber обязателен")

    base = os.getenv("BASE_URL", "https://hand-in-hand.ru").rstrip("/")
    payload = {
        "orderNumber": order_number,
        "amount": to_kopecks(amount_rub),
        "returnUrl": return_url or f"{base}/payment/return",
        "features": "FORCE_SSL",
        "description": (description or "Оплата рисунков").replace("—", "-").replace("«", "").replace("»", "")[:60],
    }
    payload.update(method_attributes(str(method).lower()))

    data = call("register.do", payload, db=db)
    err = biz_error(data, "register.do")
    if err:
        # 115 — «заказ с таким номером уже зарегистрирован»: это повтор, а не сбой.
        if err["code"] != "115" and "уже зарегистрир" not in err["message"].lower():
            raise SberError(err["message"], code=err["code"], endpoint="register.do")

    form_url = data.get("formUrl") or data.get("pageViewUrl") or ""
    if not form_url:
        raise SberError("Шлюз не вернул ссылку на платёжную форму", endpoint="register.do")
    return {"order_id": data.get("orderId"), "payment_url": form_url, "raw": data}


def map_status(order_status) -> str:
    """orderStatus шлюза → статус заказа. paid — только значение 2 (по ТЗ).

    Числовые коды — основная контракта; строковые синонимы поддерживаются на случай,
    если шлюз в конкретной версии отдаёт человекочитаемый статус.
    """
    s = str(order_status if order_status is not None else "").strip()
    code = s.split(".")[0] if re.fullmatch(r"-?\d+(\.\d+)?", s) else s.upper()
    if code == "2":
        return "paid"
    if code in ("3", "4", "5") or code in ("CANCELED", "CANCELLED", "ABORTED", "FAILED",
                                            "DECLINED", "REVERSED", "REFUNDED"):
        return "failed"
    # 0/6, известные «в процессе» и любой незнакомый код — консервативно: не paid.
    return "pending"


def get_status(order_id, db=None) -> dict:
    """Подтверждает оплату через JSON-метод getOrderStatusExtended.do.

    Для текущего API Сбера нужен ``orderId`` — UUID, полученный в ``register.do``
    и возвращаемый платёжной формой как ``mdOrder``. Числовой ``orderNumber``
    оставлен как безопасный запасной вариант для заказов, созданных до этого поля.
    """
    value = str(order_id)
    key = "orderId" if re.fullmatch(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", value) else "orderNumber"
    data = call("getOrderStatusExtended.do", {key: value}, db=db)
    err = biz_error(data, "getOrderStatusExtended.do")
    if err:
        raise SberError(err["message"], code=err["code"], endpoint="getOrderStatusExtended.do")
    return {
        "status": map_status(data.get("orderStatus")),
        "order_status": data.get("orderStatus"),
        "order_id": data.get("orderId"),
        "order_number": data.get("orderNumber"),
        "amount": data.get("amount"),
        "raw": data,
    }


def refund(order_number, amount_rub, new_order_number=None, db=None) -> dict:
    """refund.do — возврат. Без ретраев: повтор мог бы задвоить возврат."""
    payload = {
        "orderNumber": str(order_number),
        "newOrderNumber": str(new_order_number or f"R{order_number}"),
        "amount": to_kopecks(amount_rub),
        "currencyCode": str(CURRENCY_RUB),
    }
    data = call("refund.do", payload, db=db, no_retry=True)
    err = biz_error(data, "refund.do")
    if err:
        raise SberError(err["message"], code=err["code"], endpoint="refund.do")
    return data
