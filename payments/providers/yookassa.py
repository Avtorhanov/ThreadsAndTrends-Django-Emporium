"""Клиент API ЮKassa v3 (https://yookassa.ru/developers/api) на стандартной библиотеке.

Аутентификация — HTTP Basic (shopId:секретный ключ). Каждый POST идёт с заголовком
Idempotence-Key: повтор с тем же ключом возвращает тот же объект, а не создаёт новый.
Суммы у ЮKassa — строки рублей ("1500.00"); здесь они переводятся в копейки без float.
"""

import base64
import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

from django.conf import settings

from . import ProviderError, RemotePayment, RemoteRefund

logger = logging.getLogger(__name__)

CURRENCY = "RUB"
DESCRIPTION_MAX = 128


def kopecks_to_value(kopecks: int) -> str:
    return f"{kopecks // 100}.{kopecks % 100:02d}"


def value_to_kopecks(value) -> int:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ProviderError(f"Некорректная сумма от ЮKassa: {value!r}", transient=False) from exc
    kopecks = amount * 100
    if kopecks != kopecks.to_integral_value() or kopecks < 0:
        raise ProviderError(f"Некорректная сумма от ЮKassa: {value!r}", transient=False)
    return int(kopecks)


def money(kopecks: int) -> dict:
    return {"value": kopecks_to_value(kopecks), "currency": CURRENCY}


class YooKassaProvider:
    def __init__(self, shop_id: str, secret_key: str, api_url: str, timeout: int):
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_settings(cls) -> "YooKassaProvider":
        if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
            raise ProviderError(
                "ЮKassa не настроена: задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY",
                transient=True,
            )
        return cls(
            shop_id=settings.YOOKASSA_SHOP_ID,
            secret_key=settings.YOOKASSA_SECRET_KEY,
            api_url=settings.YOOKASSA_API_URL,
            timeout=settings.YOOKASSA_TIMEOUT,
        )

    # --- Платежи ---

    def create_payment(
        self,
        *,
        amount_kopecks: int,
        description: str,
        return_url: str,
        idempotency_key: str,
        metadata: dict,
        receipt: dict | None,
    ) -> RemotePayment:
        body = {
            "amount": money(amount_kopecks),
            # Одностадийная оплата: деньги списываются сразу, без подтверждения магазином.
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "description": description[:DESCRIPTION_MAX],
            "metadata": metadata,
        }
        if receipt:
            body["receipt"] = receipt
        return self._payment(self._request("POST", "/payments", body, idempotency_key))

    def get_payment(self, payment_id: str) -> RemotePayment:
        return self._payment(self._request("GET", f"/payments/{_path_id(payment_id)}"))

    # --- Возвраты ---

    def create_refund(
        self,
        *,
        payment_id: str,
        amount_kopecks: int,
        idempotency_key: str,
        description: str,
        receipt: dict | None,
    ) -> RemoteRefund:
        body = {
            "payment_id": payment_id,
            "amount": money(amount_kopecks),
            "description": description[:DESCRIPTION_MAX],
        }
        if receipt:
            body["receipt"] = receipt
        return self._refund(self._request("POST", "/refunds", body, idempotency_key))

    def get_refund(self, refund_id: str) -> RemoteRefund:
        return self._refund(self._request("GET", f"/refunds/{_path_id(refund_id)}"))

    # --- HTTP ---

    def _request(
        self, method: str, path: str, body: dict | None = None, idempotency_key: str = ""
    ) -> dict:
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        request = urllib.request.Request(f"{self.api_url}{path}", data=data, method=method)
        token = base64.b64encode(f"{self.shop_id}:{self.secret_key}".encode()).decode()
        request.add_header("Authorization", f"Basic {token}")
        request.add_header("Content-Type", "application/json")
        if idempotency_key:
            request.add_header("Idempotence-Key", idempotency_key)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            description = _error_description(exc)
            transient = exc.code >= 500 or exc.code == 429
            raise ProviderError(
                f"ЮKassa {method} {path}: HTTP {exc.code} {description}",
                transient=transient,
                status_code=exc.code,
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ProviderError(f"ЮKassa {method} {path}: {exc}", transient=True) from exc

        # 202 «запрос в обработке»: повторить позже с тем же Idempotence-Key.
        if payload.get("type") == "processing":
            raise ProviderError(f"ЮKassa {method} {path}: запрос в обработке", transient=True)
        return payload

    @staticmethod
    def _payment(data: dict) -> RemotePayment:
        try:
            return RemotePayment(
                id=str(data["id"]),
                status=str(data["status"]),
                amount_kopecks=value_to_kopecks(data["amount"]["value"]),
                currency=str(data["amount"]["currency"]),
                confirmation_url=str((data.get("confirmation") or {}).get("confirmation_url", "")),
                cancellation_reason=str(
                    (data.get("cancellation_details") or {}).get("reason", "")
                ),
                raw=data,
            )
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"Неожиданный ответ ЮKassa: {exc!r}", transient=True) from exc

    @staticmethod
    def _refund(data: dict) -> RemoteRefund:
        try:
            return RemoteRefund(
                id=str(data["id"]),
                payment_id=str(data["payment_id"]),
                status=str(data["status"]),
                amount_kopecks=value_to_kopecks(data["amount"]["value"]),
                currency=str(data["amount"]["currency"]),
                cancellation_reason=str(
                    (data.get("cancellation_details") or {}).get("reason", "")
                ),
                raw=data,
            )
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"Неожиданный ответ ЮKassa: {exc!r}", transient=True) from exc


def _path_id(value: str) -> str:
    # ID приходят из нашей БД, но в URL попадают только безопасные символы.
    if not value or not all(ch.isalnum() or ch in "-_" for ch in value):
        raise ProviderError(f"Некорректный идентификатор: {value!r}", transient=False)
    return value


def _error_description(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode() or "{}")
    except (ValueError, OSError):
        return ""
    return str(payload.get("description") or payload.get("code") or "")
