"""Оформление заказа: из всей корзины клиента или «Купить сейчас» — одна позиция мимо корзины.

Источник позиций и суммы — store.services.cart.get_summary: тот же расчёт, что видит
покупатель в корзине. Внутри транзакции:
1. блокируется строка корзины (параллельные оформления одного клиента и изменения корзины
   идут по очереди);
2. блокируются варианты корзины в порядке id (параллельные заказы разных клиентов на один
   товар — по очереди, без взаимных блокировок);
3. корзина пересчитывается и должна быть can_checkout; остатки списываются;
4. корзина очищается, письмо уходит после commit.

«Купить сейчас» (buy_now): позиция считается тем же расчётом (quote), блокировки и списание —
те же, корзина не меняется.

Повторный сабмит с тем же Idempotency-Key возвращает уже созданный заказ.
"""

import re
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import F

from content import shop as shop_settings
from orders.models import (
    ORDER_NUMBER_PREFIX,
    ORDER_NUMBER_SEQUENCE,
    ChangedBy,
    DeliveryMethod,
    Order,
    OrderItem,
    OrderStatusChange,
    PaymentMethod,
)
from store.models import Cart, ProductVariant
from store.services.cart import CartSummary, LineInput, get_summary, quote
from store.templatetags.money import format_kopecks

from . import notifications
from .status import initial_status

IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
EMPTY_CART = "Корзина пуста."
BUY_NOW_CHANGED = "Товар изменился — проверьте его на странице товара"


@dataclass(frozen=True)
class CheckoutInput:
    delivery_method: str
    payment_method: str
    recipient_name: str
    recipient_phone: str
    delivery_address: str = ""
    comment: str = ""
    # Сумма, которую покупатель видел на экране оформления. Если не совпала с пересчитанной
    # (цена изменилась), заказ не создаётся.
    expected_total_kopecks: int | None = None


@dataclass(frozen=True)
class DeliveryOption:
    method: str
    title: str
    cost_kopecks: int
    address: str = ""  # адрес пункта самовывоза


@dataclass(frozen=True)
class RecipientDefaults:
    recipient_name: str = ""
    recipient_phone: str = ""
    delivery_address: str = ""


@dataclass(frozen=True)
class CheckoutPreview:
    cart: CartSummary
    delivery_options: list[DeliveryOption]
    payment_methods: list[str]
    free_delivery_from_kopecks: int
    defaults: RecipientDefaults = field(default_factory=RecipientDefaults)


# --- Условия доставки и оплаты (панель → «Настройки», пустое поле — .env) ---


def delivery_cost(method: str, items_total_kopecks: int) -> int:
    if method == DeliveryMethod.PICKUP:
        return 0
    shop = shop_settings.current()
    if items_total_kopecks >= shop.delivery_free_from_kopecks:
        return 0
    return shop.delivery_courier_kopecks


def delivery_options(items_total_kopecks: int) -> list[DeliveryOption]:
    options = [
        DeliveryOption(
            method=DeliveryMethod.COURIER,
            title=DeliveryMethod.COURIER.label,
            cost_kopecks=delivery_cost(DeliveryMethod.COURIER, items_total_kopecks),
        )
    ]
    pickup_address = shop_settings.current().pickup_address
    if pickup_address:
        options.append(
            DeliveryOption(
                method=DeliveryMethod.PICKUP,
                title=DeliveryMethod.PICKUP.label,
                cost_kopecks=0,
                address=pickup_address,
            )
        )
    return options


def payment_methods() -> list[str]:
    shop = shop_settings.current()
    methods = []
    if shop.online_payment:
        methods.append(PaymentMethod.ONLINE.value)
    if shop.cash_on_delivery:
        methods.append(PaymentMethod.ON_DELIVERY.value)
    return methods


def _summary(user, buy_now: LineInput | None) -> CartSummary:
    return quote([buy_now]) if buy_now is not None else get_summary(user)


def preview(user, buy_now: LineInput | None = None) -> CheckoutPreview:
    """Данные экрана оформления: корзина (или одна позиция «Купить сейчас»), способы доставки
    с ценой, подстановка получателя из последнего заказа."""
    summary = _summary(user, buy_now)
    last = (
        Order.objects.filter(owner=user)
        .order_by("-created_at", "-id")
        .values("recipient_name", "recipient_phone", "delivery_address", "delivery_method")
        .first()
    )
    defaults = RecipientDefaults()
    if last:
        defaults = RecipientDefaults(
            recipient_name=last["recipient_name"],
            recipient_phone=last["recipient_phone"],
            # Адрес самовывоза — не адрес клиента, его не подставляем.
            delivery_address=(
                last["delivery_address"]
                if last["delivery_method"] == DeliveryMethod.COURIER
                else ""
            ),
        )
    return CheckoutPreview(
        cart=summary,
        delivery_options=delivery_options(summary.total_kopecks),
        payment_methods=payment_methods(),
        free_delivery_from_kopecks=shop_settings.current().delivery_free_from_kopecks,
        defaults=defaults,
    )


# --- Проверка ввода ---


def normalize_phone(value: str) -> str:
    """Российский номер → +7XXXXXXXXXX. Принимает 8…, +7…, 7… и 10 цифр, разделители
    (пробелы, скобки, дефисы) игнорируются."""
    raw = (value or "").strip()
    if re.search(r"[^\d\s()+\-]", raw):
        raise ValidationError("Введите российский номер телефона, например +7 900 123-45-67.")
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] in "78":
        digits = digits[1:]
    if len(digits) != 10 or digits[0] not in "3489":
        raise ValidationError("Введите российский номер телефона, например +7 900 123-45-67.")
    return f"+7{digits}"


def _clean_input(data: CheckoutInput) -> dict:
    errors: dict[str, list[str]] = {}
    cleaned: dict = {}

    if data.delivery_method not in {option.method for option in delivery_options(0)}:
        errors["delivery_method"] = ["Этот способ доставки недоступен."]
    if data.payment_method not in payment_methods():
        errors["payment_method"] = ["Этот способ оплаты недоступен."]

    name = " ".join((data.recipient_name or "").split())
    if len(name) < 2:
        errors["recipient_name"] = ["Укажите имя и фамилию получателя."]
    cleaned["recipient_name"] = name

    try:
        cleaned["recipient_phone"] = normalize_phone(data.recipient_phone)
    except ValidationError as exc:
        errors["recipient_phone"] = exc.messages

    address = " ".join((data.delivery_address or "").split())
    if data.delivery_method == DeliveryMethod.PICKUP:
        address = shop_settings.current().pickup_address  # снимок адреса пункта выдачи
    elif len(address) < 5:
        errors["delivery_address"] = ["Укажите адрес доставки: город, улицу, дом и квартиру."]
    cleaned["delivery_address"] = address
    cleaned["comment"] = (data.comment or "").strip()

    if errors:
        raise ValidationError(errors)
    return cleaned


def _validate_key(key: str) -> None:
    if not key or not IDEMPOTENCY_KEY_RE.match(key):
        raise ValidationError(
            "Заголовок Idempotency-Key обязателен: 8–64 символа (латиница, цифры, - и _).",
            code="idempotency_key",
        )


# --- Оформление ---


def _find_existing(user, key: str) -> Order | None:
    return Order.objects.filter(owner=user, idempotency_key=key).first()


def _next_number() -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [ORDER_NUMBER_SEQUENCE])
        (value,) = cursor.fetchone()
    return f"{ORDER_NUMBER_PREFIX}{value}"


def _problems_message(summary: CartSummary, buy_now: bool = False) -> str:
    names = [
        line.product.name if line.product else "товар снят с продажи"
        for line in summary.lines
        if line.status != "ok"
    ]
    head = BUY_NOW_CHANGED if buy_now else "Корзина изменилась — проверьте позиции"
    return head + ": " + ", ".join(names) + "."


def checkout(
    user, data: CheckoutInput, idempotency_key: str, buy_now: LineInput | None = None
) -> tuple[Order, bool]:
    """Оформить заказ из всей корзины или одну позицию buy_now (корзина не меняется).
    Возвращает (заказ, создан_сейчас)."""
    _validate_key(idempotency_key)
    existing = _find_existing(user, idempotency_key)
    if existing is not None:
        return existing, False
    cleaned = _clean_input(data)

    try:
        with transaction.atomic():
            cart = Cart.objects.select_for_update().filter(owner=user).first()
            # Параллельный запрос с тем же ключом ждал блокировку корзины и видит готовый заказ.
            existing = _find_existing(user, idempotency_key)
            if existing is not None:
                return existing, False
            if buy_now is not None:
                variant_ids = [buy_now.variant_id]
            else:
                if cart is None:
                    raise ValidationError(EMPTY_CART, code="empty_cart")
                variant_ids = list(cart.items.values_list("variant_id", flat=True))
                if not variant_ids:
                    raise ValidationError(EMPTY_CART, code="empty_cart")
            list(
                ProductVariant.all_objects.select_for_update()
                .filter(pk__in=variant_ids)
                .order_by("pk")
                .values_list("pk", flat=True)
            )

            # Пересчёт под блокировкой: остатки не изменятся до commit.
            summary = _summary(user, buy_now)
            if not summary.lines:
                raise ValidationError(EMPTY_CART, code="empty_cart")
            if not summary.can_checkout:
                raise ValidationError(
                    _problems_message(summary, buy_now is not None), code="cart_changed"
                )

            items_total = summary.total_kopecks
            delivery = delivery_cost(data.delivery_method, items_total)
            total = items_total + delivery
            expected = data.expected_total_kopecks
            if expected is not None and expected != total:
                raise ValidationError(
                    f"Сумма заказа изменилась: теперь {format_kopecks(total)} ₽. "
                    "Проверьте заказ и подтвердите ещё раз.",
                    code="total_changed",
                )

            order = Order.objects.create(
                owner=user,
                number=_next_number(),
                status=initial_status(data.payment_method),
                payment_method=data.payment_method,
                delivery_method=data.delivery_method,
                items_total_kopecks=items_total,
                delivery_kopecks=delivery,
                total_kopecks=total,
                idempotency_key=idempotency_key,
                **cleaned,
            )
            lines = sorted(summary.lines, key=lambda line: line.variant_id)
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=line.variant.product,
                        variant=line.variant,
                        product_name=line.variant.product.name,
                        size=line.variant.size,
                        sku=line.variant.sku,
                        status_name=_status_name(line.variant.product),
                        price_kopecks=line.unit_price_kopecks,
                        quantity=line.quantity,
                    )
                    for line in lines
                ]
            )
            for line in lines:
                updated = ProductVariant.all_objects.filter(
                    pk=line.variant_id, stock__gte=line.quantity
                ).update(stock=F("stock") - line.quantity)
                if updated != 1:  # невозможно под блокировкой; страховка от отрицательных остатков
                    raise ValidationError(_problems_message(summary), code="cart_changed")

            sent = notifications.notify_status(order, created=True)
            OrderStatusChange.objects.create(
                order=order,
                from_status="",
                to_status=order.status,
                changed_by=ChangedBy.CUSTOMER,
                actor=user,
                notified=sent,
            )
            if buy_now is None:
                cart.items.all().delete()
    except IntegrityError:
        # Гонка по уникальному ключу (owner, idempotency_key) без корзины-блокировки.
        existing = _find_existing(user, idempotency_key)
        if existing is None:
            raise
        return existing, False
    return order, True


def _status_name(product) -> str:
    status = product.status if product.status_id else None
    return status.name if status else ""
