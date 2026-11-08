"""Гостевые заказы: секретная ссылка, привязка к аккаунту, обезличивание.

Токен выводится из ключа идемпотентности и SECRET_KEY: повтор оформления возвращает ту же
ссылку, хотя в БД лежит только её хеш (утечка базы ссылок не раскрывает). Неверный или
просроченный токен неотличим от отсутствующего — вызывающий отвечает 404.
"""

import hashlib
import re
from datetime import timedelta

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.crypto import salted_hmac

from orders.models import Order

LINK_LIFETIME = timedelta(days=30)  # после завершения заказа
RETENTION = timedelta(days=180)  # после завершения заказа
MAX_CLAIM_TOKENS = 20
TOKEN_RE = re.compile(r"^[0-9a-f]{64}$")
_SALT = "orders.guest.order-link"


def make_token(idempotency_key: str) -> str:
    return salted_hmac(_SALT, idempotency_key, algorithm="sha256").hexdigest()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def by_token(token: str) -> QuerySet[Order]:
    """Гостевой заказ по действующей ссылке; пустая выборка — ссылки нет или она истекла."""
    if not TOKEN_RE.match(token or ""):
        return Order.objects.none()
    return Order.objects.filter(
        Q(guest_link_expires_at__isnull=True) | Q(guest_link_expires_at__gt=timezone.now()),
        owner__isnull=True,
        guest_token_hash=token_hash(token),
    )


def claim(user, tokens) -> list[Order]:
    """Привязать к аккаунту заказы по действующим ссылкам; ссылки после этого не работают.
    Владение доказывает только токен: телефон не подтверждён и в сопоставлении не участвует."""
    if user.is_staff:
        return []
    hashes = {token_hash(t) for t in list(tokens)[:MAX_CLAIM_TOKENS] if TOKEN_RE.match(t or "")}
    if not hashes:
        return []
    claimed: list[Order] = []
    with transaction.atomic():
        candidates = (
            Order.objects.select_for_update()
            .filter(
                Q(guest_link_expires_at__isnull=True) | Q(guest_link_expires_at__gt=timezone.now()),
                owner__isnull=True,
                guest_token_hash__in=hashes,
            )
            .order_by("pk")
        )
        for order in candidates:
            # UNIQUE(owner, idempotency_key): при совпадении заказ остаётся гостевым.
            if Order.objects.filter(owner=user, idempotency_key=order.idempotency_key).exists():
                continue
            order.owner = user
            order.guest_token_hash = ""
            order.guest_link_expires_at = None
            order.save(
                update_fields=["owner", "guest_token_hash", "guest_link_expires_at", "updated_at"]
            )
            claimed.append(order)
    return claimed


def anonymize_old() -> int:
    """У гостя нет кнопки удаления: получатель стирается сам, заказ остаётся для учёта."""
    # guest_link_expires_at = завершение + LINK_LIFETIME.
    threshold = timezone.now() - (RETENTION - LINK_LIFETIME)
    return (
        Order.objects.filter(owner__isnull=True, guest_link_expires_at__lte=threshold)
        .exclude(recipient_name="", recipient_phone="", delivery_address="", comment="")
        .update(recipient_name="", recipient_phone="", delivery_address="", comment="")
    )
