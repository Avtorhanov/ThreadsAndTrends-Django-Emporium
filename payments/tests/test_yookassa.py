"""Клиент ЮKassa без сети: urlopen подменяется, проверяются запросы и разбор ответов."""

import base64
import io
import json
import urllib.error

import pytest

from payments.providers import ProviderError
from payments.providers import yookassa
from payments.providers.yookassa import YooKassaProvider, kopecks_to_value, value_to_kopecks

PAYMENT = {
    "id": "2d5e4c11-000f-5000-9000-1d5d0c1b2a3f",
    "status": "pending",
    "paid": False,
    "amount": {"value": "3000.00", "currency": "RUB"},
    "confirmation": {
        "type": "redirect",
        "confirmation_url": "https://yoomoney.ru/checkout/payments/v2/contract?orderId=2d5e",
    },
    "created_at": "2026-10-13T10:00:00.000Z",
    "test": True,
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def http(monkeypatch):
    """Подмена urlopen: queue — ответы (dict или исключение), requests — отправленные запросы."""
    state = {"queue": [], "requests": []}

    def urlopen(request, timeout):
        state["requests"].append(request)
        answer = state["queue"].pop(0)
        if isinstance(answer, Exception):
            raise answer
        return FakeResponse(json.dumps(answer).encode())

    monkeypatch.setattr(yookassa.urllib.request, "urlopen", urlopen)
    return state


@pytest.fixture
def provider():
    return YooKassaProvider("123456", "test_secret", "https://api.yookassa.ru/v3", timeout=5)


def http_error(code, body):
    return urllib.error.HTTPError(
        "https://api.yookassa.ru/v3/payments", code, "error", {}, io.BytesIO(json.dumps(body).encode())
    )


@pytest.mark.parametrize(
    ("kopecks", "value"), [(0, "0.00"), (5, "0.05"), (150_000, "1500.00"), (123_456, "1234.56")]
)
def test_money_conversion(kopecks, value):
    assert kopecks_to_value(kopecks) == value
    assert value_to_kopecks(value) == kopecks


@pytest.mark.parametrize("value", ["1.005", "abc", "-1.00"])
def test_bad_amount_is_rejected(value):
    with pytest.raises(ProviderError):
        value_to_kopecks(value)


def test_create_payment_request(http, provider):
    http["queue"].append(PAYMENT)
    receipt = {"customer": {"email": "a@example.com"}, "items": [], "tax_system_code": 2}

    remote = provider.create_payment(
        amount_kopecks=300_000,
        description="Заказ DD-100001 в DiDi-shop",
        return_url="didishop://orders/DD-100001",
        idempotency_key="key-1",
        metadata={"order_number": "DD-100001"},
        receipt=receipt,
    )

    [request] = http["requests"]
    assert request.full_url == "https://api.yookassa.ru/v3/payments"
    assert request.get_method() == "POST"
    assert request.get_header("Idempotence-key") == "key-1"
    token = base64.b64encode(b"123456:test_secret").decode()
    assert request.get_header("Authorization") == f"Basic {token}"
    body = json.loads(request.data)
    assert body["amount"] == {"value": "3000.00", "currency": "RUB"}
    assert body["capture"] is True
    assert body["confirmation"] == {"type": "redirect", "return_url": "didishop://orders/DD-100001"}
    assert body["receipt"] == receipt
    assert remote.id == PAYMENT["id"]
    assert remote.status == "pending"
    assert remote.amount_kopecks == 300_000
    assert remote.confirmation_url.startswith("https://yoomoney.ru/")


def test_get_payment_with_cancellation(http, provider):
    http["queue"].append(
        {**PAYMENT, "status": "canceled", "cancellation_details": {"reason": "expired_on_confirmation"}}
    )
    remote = provider.get_payment(PAYMENT["id"])
    assert http["requests"][0].get_method() == "GET"
    assert remote.status == "canceled"
    assert remote.cancellation_reason == "expired_on_confirmation"


def test_refund_request(http, provider):
    http["queue"].append(
        {
            "id": "216749f7-0016-50be-b000-078d43a63ae4",
            "payment_id": PAYMENT["id"],
            "status": "succeeded",
            "amount": {"value": "3000.00", "currency": "RUB"},
        }
    )
    remote = provider.create_refund(
        payment_id=PAYMENT["id"],
        amount_kopecks=300_000,
        idempotency_key="refund-key",
        description="Возврат по заказу DD-100001",
        receipt=None,
    )
    body = json.loads(http["requests"][0].data)
    assert body == {
        "payment_id": PAYMENT["id"],
        "amount": {"value": "3000.00", "currency": "RUB"},
        "description": "Возврат по заказу DD-100001",
    }
    assert remote.status == "succeeded" and remote.amount_kopecks == 300_000


@pytest.mark.parametrize(
    ("error", "transient"),
    [
        (http_error(400, {"type": "error", "code": "invalid_request"}), False),
        (http_error(401, {"type": "error", "code": "invalid_credentials"}), False),
        (http_error(429, {"type": "error", "code": "too_many_requests"}), True),
        (http_error(500, {"type": "error", "code": "internal_server_error"}), True),
        (urllib.error.URLError("timed out"), True),
        (TimeoutError("timed out"), True),
    ],
)
def test_errors_are_classified(http, provider, error, transient):
    http["queue"].append(error)
    with pytest.raises(ProviderError) as exc:
        provider.get_payment(PAYMENT["id"])
    assert exc.value.transient is transient


def test_processing_response_is_transient(http, provider):
    http["queue"].append({"type": "processing", "retry_after": 1800})
    with pytest.raises(ProviderError) as exc:
        provider.get_payment(PAYMENT["id"])
    assert exc.value.transient is True


def test_unsafe_id_is_not_sent(http, provider):
    with pytest.raises(ProviderError):
        provider.get_payment("../refunds")
    assert http["requests"] == []


def test_from_settings_requires_keys(settings):
    settings.YOOKASSA_SHOP_ID = ""
    with pytest.raises(ProviderError) as exc:
        YooKassaProvider.from_settings()
    assert exc.value.transient is True
