"""Платёжный провайдер: общий интерфейс и выбор реализации.

Сервисы работают только с RemotePayment/RemoteRefund и ProviderError — замена провайдера
не затрагивает модели и бизнес-логику. В тестах get_provider подменяется фейком.
"""

from dataclasses import dataclass, field
from typing import Protocol


class ProviderError(Exception):
    """Ошибка обращения к провайдеру.

    transient=True — сеть, таймаут, 5xx, 429 или «запрос в обработке»: повторить позже с тем же
    ключом идемпотентности. transient=False — провайдер отклонил запрос (4xx): повтор не поможет.
    """

    def __init__(self, message: str, *, transient: bool, status_code: int | None = None):
        super().__init__(message)
        self.transient = transient
        self.status_code = status_code


@dataclass(frozen=True)
class RemotePayment:
    id: str
    # pending | waiting_for_capture | succeeded | canceled
    status: str
    amount_kopecks: int
    currency: str
    confirmation_url: str = ""
    cancellation_reason: str = ""
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RemoteRefund:
    id: str
    payment_id: str
    # pending | succeeded | canceled
    status: str
    amount_kopecks: int
    currency: str
    cancellation_reason: str = ""
    raw: dict = field(default_factory=dict)


class PaymentProvider(Protocol):
    def create_payment(
        self,
        *,
        amount_kopecks: int,
        description: str,
        return_url: str,
        idempotency_key: str,
        metadata: dict,
        receipt: dict | None,
    ) -> RemotePayment: ...

    def get_payment(self, payment_id: str) -> RemotePayment: ...

    def create_refund(
        self,
        *,
        payment_id: str,
        amount_kopecks: int,
        idempotency_key: str,
        description: str,
        receipt: dict | None,
    ) -> RemoteRefund: ...

    def get_refund(self, refund_id: str) -> RemoteRefund: ...


def get_provider() -> PaymentProvider:
    from .yookassa import YooKassaProvider

    return YooKassaProvider.from_settings()
