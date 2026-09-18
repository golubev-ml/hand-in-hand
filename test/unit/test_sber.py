"""Юнит-тесты адаптера платежей Сбербанка (HIH-9). Шлюз — мок, сети нет."""
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "back"))

from payments import sber  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """Тестовый контур, фиксированная учётка и сбор логов вместо БД."""
    monkeypatch.setenv("SBER_BASE_URL", "https://mock.sber/ecomm/gateway/api/rest/")
    monkeypatch.setenv("BASE_URL", "https://hand-in-hand.ru")
    monkeypatch.setenv("SBER_USER_NAME", "unit-user")
    monkeypatch.setenv("SBER_PASSWORD", "unit-secret-key")
    monkeypatch.delenv("SBER_METHOD_ATTRS_JSON", raising=False)
    logs = []
    monkeypatch.setattr(sber, "log_exchange",
                        lambda text, url, request, response: logs.append(
                            {"text": text, "url": url, "request": request, "response": response}))
    yield {"logs": logs}


@pytest.fixture
def gateway(monkeypatch, isolated_env):
    """Подменяет транспорт моком; handler(request) -> httpx.Response."""
    state = {"requests": [], "script": []}

    def handler(request: httpx.Request) -> httpx.Response:
        state["requests"].append(request)
        body = dict(httpx.QueryParams(request.url.query)) if request.method == "GET" else \
            dict(httpx.QueryParams(request.content.decode("utf-8")))
        state.setdefault("bodies", []).append(body)
        reply = state["script"].pop(0) if state["script"] else {"error": "нет смоделированного ответа"}
        if callable(reply):
            return reply(request)
        return httpx.Response(reply.get("status", 200),
                              json=reply.get("json", {}),
                              text=reply.get("text"))

    transport = httpx.MockTransport(handler)

    def _set(responses):
        state["script"] = list(responses)

    monkeypatch.setattr(sber, "_transport", transport)
    state["set_responses"] = _set
    state["last_body"] = lambda: state["bodies"][-1]
    return state


# ─── вспомогательные функции ──────────────────────────────────────────────────

def test_base_url_uses_env_and_defaults_to_test_contour(monkeypatch):
    monkeypatch.setenv("SBER_BASE_URL", "https://securepay.sberbank.ru/ecomm/gateway/api/rest/")
    assert sber.base_url() == "https://securepay.sberbank.ru/ecomm/gateway/api/rest/"
    monkeypatch.delenv("SBER_BASE_URL")
    assert sber.base_url() == sber.TEST_BASE_URL
    assert sber.TEST_BASE_URL.startswith("https://ecomtest.sberbank.ru/")
    assert sber.PROD_BASE_URL.startswith("https://securepayments.sberbank.ru/")


@pytest.mark.parametrize("rub,kopecks", [
    (500, 50000), (2500, 250000), (10.5, 1050), ("1500", 150000), (0.01, 1),
])
def test_amount_in_kopecks(rub, kopecks):
    assert sber.to_kopecks(rub) == kopecks


@pytest.mark.parametrize("bad", [0, -1, None, "abc", ""])
def test_bad_amount_rejected(bad):
    with pytest.raises(sber.SberError):
        sber.to_kopecks(bad)


@pytest.mark.parametrize("gateway_status,internal", [
    (2, "paid"), (0, "pending"), (6, "pending"), (3, "failed"), (4, "failed"), (5, "failed"),
    ("2", "paid"), (2.0, "paid"), (None, "pending"), ("", "pending"),
    ("WHATEVER_UNKNOWN", "pending"),
])
def test_map_status_from_spec(gateway_status, internal):
    assert sber.map_status(gateway_status) == internal


def test_only_numeric_two_marks_paid():
    """По ТЗ paid — только orderStatus 2. Человекочитаемые синонимы оплаченными не считаются."""
    assert sber.map_status("DONE") == "pending"
    assert sber.map_status("COMPLETED") == "pending"
    assert sber.map_status(1) == "pending"


def test_map_status_string_synonyms():
    assert sber.map_status("CANCELED") == "failed"
    assert sber.map_status("AUTHORIZED") == "pending"


@pytest.mark.parametrize("method", ["card", "sbp", "sberpay", "mirpay", "unknown"])
def test_method_attributes(method):
    attrs = sber.method_attributes(method)
    if method == "card":
        assert attrs == {}
    elif method == "sberpay":
        assert "sberbankOnlineAttributes" in attrs["jsonParams"]      # обязателен по ТЗ
    elif method == "sbp":
        assert "sbpAttributes" in attrs["jsonParams"]
    elif method == "mirpay":
        assert "mirPayAttributes" in attrs["jsonParams"]
    else:
        assert attrs == {}


def test_sberpay_always_keeps_required_block(monkeypatch):
    """Даже при пустом переопределении jsonParams.sberbankOnlineAttributes обязан остаться."""
    monkeypatch.setenv("SBER_METHOD_ATTRS_JSON", json.dumps({"sberpay": {}}))
    assert "sberbankOnlineAttributes" in sber.method_attributes("sberpay")["jsonParams"]


# ─── register.do ──────────────────────────────────────────────────────────────

def test_create_payment_payload(gateway):
    gateway["set_responses"]([{"json": {"orderId": "100500", "formUrl": "https://pay.sber/form/1"}}])
    result = sber.create_payment(order_number=42, amount_rub=2500, method="sberpay")

    body = gateway["last_body"]()
    assert result["payment_url"] == "https://pay.sber/form/1"
    assert result["order_id"] == "100500"
    assert body["orderNumber"] == "42"
    assert body["amount"] == "250000"                 # копейки
    assert body["currencyCode"] == "643"
    assert body["returnUrl"] == "https://hand-in-hand.ru/payment/return"
    assert body["failUrl"] == "https://hand-in-hand.ru/payment/fail"
    assert body["userName"] == "unit-user"
    assert body["password"] == "unit-secret-key"
    assert "sberbankOnlineAttributes" in body["jsonParams"]


def test_create_payment_uses_page_view_url(gateway):
    gateway["set_responses"]([{"json": {"orderId": "7", "pageViewUrl": "https://pay.sber/view"}}])
    assert sber.create_payment(1, 500)["payment_url"] == "https://pay.sber/view"


def test_create_payment_without_form_url_fails(gateway):
    gateway["set_responses"]([{"json": {"orderId": "7"}}])
    with pytest.raises(sber.SberError):
        sber.create_payment(1, 500)


def test_create_payment_rejects_unknown_method(gateway):
    with pytest.raises(sber.SberError):
        sber.create_payment(1, 500, method="paypal")
    assert gateway["requests"] == []                  # до шлюза не дошло


def test_error_code_115_is_idempotent_repeat(gateway):
    gateway["set_responses"]([{"json": {"errorCode": "115", "errorMessage": "Заказ с таким номером уже зарегистрирован",
                                        "orderId": "55", "formUrl": "https://pay.sber/f/55"}}])
    assert sber.create_payment(5, 500)["order_id"] == "55"


def test_other_error_code_raises(gateway):
    gateway["set_responses"]([{"json": {"errorCode": "101", "errorMessage": "Неверные учётные данные"}}])
    with pytest.raises(sber.SberError) as exc:
        sber.create_payment(6, 500)
    assert exc.value.code == "101"


def test_zero_error_code_is_success(gateway):
    gateway["set_responses"]([{"json": {"errorCode": "0", "orderId": "9", "formUrl": "https://pay/f"}}])
    assert sber.create_payment(9, 500)["order_id"] == "9"


# ─── getOrderStatus.do ────────────────────────────────────────────────────────

def test_get_status_uses_get_and_maps(gateway):
    gateway["set_responses"]([{"json": {"orderStatus": 2, "orderId": "123", "amount": 50000,
                                        "orderNumber": "12"}}])
    status = sber.get_status(12)
    request = gateway["requests"][-1]
    assert request.method == "GET"
    assert request.url.params["orderNumber"] == "12"
    assert status["status"] == "paid"
    assert status["amount"] == 50000


def test_get_status_error_raises(gateway):
    gateway["set_responses"]([{"json": {"errorCode": "118", "errorMessage": "Заказ не найден"}}])
    with pytest.raises(sber.SberError) as exc:
        sber.get_status(999)
    assert exc.value.code == "118"


# ─── refund.do / retry / лог ─────────────────────────────────────────────────

def test_refund_payload(gateway):
    gateway["set_responses"]([{"json": {"orderId": "1", "refundId": "2"}}])
    sber.refund(12, 2500)
    body = gateway["last_body"]()
    assert body["amount"] == "250000"
    assert body["newOrderNumber"].startswith("R12")


def test_refund_does_not_retry_on_500(gateway, monkeypatch):
    monkeypatch.setattr(sber, "RETRIES", 2)
    gateway["set_responses"]([{"status": 500, "json": {}}])
    with pytest.raises(sber.SberError):
        sber.refund(12, 100)
    assert len(gateway["requests"]) == 1              # ни одного повтора


def test_gateway_503_retries_for_registration(gateway, monkeypatch):
    monkeypatch.setattr(sber, "RETRIES", 2)
    monkeypatch.setattr(sber.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def flaky(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"orderId": "1", "formUrl": "https://pay/1"})

    gateway["set_responses"]([flaky, flaky])
    assert sber.create_payment(3, 100)["payment_url"] == "https://pay/1"
    assert calls["n"] == 2


def test_non_json_answer_handled(gateway):
    gateway["set_responses"]([{"status": 200, "text": "<html>gateway unavailable</html>"}])
    with pytest.raises(sber.SberError):
        sber.create_payment(4, 100)


def test_log_contains_exchange_and_masks_secret(gateway, isolated_env):
    gateway["set_responses"]([{"json": {"orderId": "1", "formUrl": "https://pay/1"}}])
    sber.create_payment(2, 100)
    logs = isolated_env["logs"]
    assert any("register.do" in entry["text"] for entry in logs)
    blob = json.dumps(logs, ensure_ascii=False)
    assert "unit-secret-key" not in blob              # ключ мерчанта не светится в логе
    assert '"password": "***"' in logs[0]["request"]


def test_is_configured_from_env_only(monkeypatch):
    monkeypatch.delenv("SBER_USER_NAME", raising=False)
    monkeypatch.delenv("SBER_PASSWORD", raising=False)
    assert sber.is_configured(None) is False
    monkeypatch.setenv("SBER_USER_NAME", "u")
    monkeypatch.setenv("SBER_PASSWORD", "k")
    assert sber.is_configured(None) is True


def test_redact_masks_nested_secrets():
    data = {"userName": "u", "password": "s", "jsonParams": {"secret": "x", "keep": 1},
            "key_id": "k9", "orderNumber": "5"}
    out = sber.redact(data)
    assert out["password"] == "***" and out["jsonParams"]["secret"] == "***"
    assert out["jsonParams"]["keep"] == 1 and out["orderNumber"] == "5"
    assert out["key_id"] == "***"
