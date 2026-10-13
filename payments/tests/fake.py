"""Фейковый провайдер: ведёт себя как ЮKassa (идемпотентность по ключу, статусы, суммы),
но в памяти. Тест управляет «покупателем» через pay()/decline() и сбоями через down/fail_next."""

import threading

from payments.providers import ProviderError, RemotePayment, RemoteRefund


class FakeProvider:
    def __init__(self):
        self.payments: dict[str, dict] = {}
        self.refunds: dict[str, dict] = {}
        self._payment_keys: dict[str, str] = {}
        self._refund_keys: dict[str, str] = {}
        self.calls: list[str] = []
        self.down = False  # все вызовы — временная ошибка
        self.fail_next: ProviderError | None = None  # одна ошибка на следующий вызов
        self.refund_status = "succeeded"  # статус, с которым создаются возвраты
        self._lock = threading.Lock()

    # --- управление из тестов ---

    def pay(self, payment_id: str, amount_kopecks: int | None = None, currency: str = "RUB"):
        payment = self.payments[payment_id]
        payment["status"] = "succeeded"
        if amount_kopecks is not None:
            payment["amount"] = amount_kopecks
        payment["currency"] = currency

    def decline(self, payment_id: str, reason: str = "insufficient_funds"):
        self.payments[payment_id].update(status="canceled", reason=reason)

    def only_payment_id(self) -> str:
        assert len(self.payments) == 1, self.payments
        return next(iter(self.payments))

    # --- интерфейс провайдера ---

    def _call(self, name: str):
        self.calls.append(name)
        if self.down:
            raise ProviderError("провайдер недоступен", transient=True)
        if self.fail_next is not None:
            error, self.fail_next = self.fail_next, None
            raise error

    def _payment(self, payment_id: str) -> RemotePayment:
        p = self.payments[payment_id]
        return RemotePayment(
            id=payment_id,
            status=p["status"],
            amount_kopecks=p["amount"],
            currency=p["currency"],
            confirmation_url=f"https://yoomoney.test/checkout?orderId={payment_id}",
            cancellation_reason=p.get("reason", ""),
            raw={"id": payment_id, "status": p["status"]},
        )

    def _refund(self, refund_id: str) -> RemoteRefund:
        r = self.refunds[refund_id]
        return RemoteRefund(
            id=refund_id,
            payment_id=r["payment_id"],
            status=r["status"],
            amount_kopecks=r["amount"],
            currency="RUB",
            cancellation_reason=r.get("reason", ""),
            raw={"id": refund_id, "status": r["status"]},
        )

    def create_payment(
        self, *, amount_kopecks, description, return_url, idempotency_key, metadata, receipt
    ):
        with self._lock:
            self._call("create_payment")
            if idempotency_key not in self._payment_keys:
                payment_id = f"pay-{len(self.payments) + 1:04d}"
                self.payments[payment_id] = {
                    "status": "pending",
                    "amount": amount_kopecks,
                    "currency": "RUB",
                    "return_url": return_url,
                    "metadata": metadata,
                    "receipt": receipt,
                    "description": description,
                }
                self._payment_keys[idempotency_key] = payment_id
            return self._payment(self._payment_keys[idempotency_key])

    def get_payment(self, payment_id):
        with self._lock:
            self._call("get_payment")
            if payment_id not in self.payments:
                raise ProviderError("not found", transient=False, status_code=404)
            return self._payment(payment_id)

    def create_refund(self, *, payment_id, amount_kopecks, idempotency_key, description, receipt):
        with self._lock:
            self._call("create_refund")
            if idempotency_key not in self._refund_keys:
                refund_id = f"ref-{len(self.refunds) + 1:04d}"
                self.refunds[refund_id] = {
                    "payment_id": payment_id,
                    "amount": amount_kopecks,
                    "status": self.refund_status,
                    "receipt": receipt,
                }
                self._refund_keys[idempotency_key] = refund_id
            return self._refund(self._refund_keys[idempotency_key])

    def get_refund(self, refund_id):
        with self._lock:
            self._call("get_refund")
            if refund_id not in self.refunds:
                raise ProviderError("not found", transient=False, status_code=404)
            return self._refund(refund_id)
