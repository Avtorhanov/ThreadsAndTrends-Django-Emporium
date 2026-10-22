"""Корзина: одна логика для клиента (корзина в БД) и гостя (позиции хранит клиент: устройство
в приложении, сессия на веб-витрине — операции guest_* ниже).

Цена в корзине не хранится — сумма всегда считается от текущей цены товара. Состояние
корзины (CartSummary) строит одна функция `_summarize` и для сохранённой корзины, и для
гостевой (`quote`). Оформление заказа (сессия 5) берёт тот же `get_summary` и требует
`can_checkout`, поэтому показанная сумма совпадает с суммой заказа.

Ошибки — django ValidationError (→ 400) и Http404 (чужая или несуществующая позиция).
"""

from collections.abc import Iterable
from dataclasses import dataclass, field, replace

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Exists, OuterRef, Subquery
from django.http import Http404

from store.models import Cart, CartItem, Product, ProductVariant


class LineStatus(models.TextChoices):
    OK = "ok", "Доступна"
    # Товар или вариант удалён, скрыт (сам или его категория) либо не существует.
    UNAVAILABLE = "unavailable", "Недоступна"
    OUT_OF_STOCK = "out_of_stock", "Нет в наличии"
    # В корзине больше, чем можно купить сейчас (остаток уменьшился).
    EXCEEDS_STOCK = "exceeds_stock", "Превышает остаток"


class MergeNoticeReason(models.TextChoices):
    UNAVAILABLE = "unavailable", "Товар недоступен — не перенесён"
    OUT_OF_STOCK = "out_of_stock", "Нет в наличии — не перенесён"
    CART_FULL = "cart_full", "Корзина заполнена — не перенесён"
    QUANTITY_LIMITED = "quantity_limited", "Количество уменьшено до доступного"


@dataclass(frozen=True)
class LineInput:
    """Позиция гостевой корзины (с устройства) или строка сохранённой корзины."""

    variant_id: int
    quantity: int
    seen_price_kopecks: int | None = None


@dataclass(frozen=True)
class CartLine:
    id: int | None  # id CartItem; None — гостевая позиция
    variant_id: int
    variant: ProductVariant | None  # None — варианта не существует
    quantity: int
    status: str
    max_quantity: int  # сколько можно купить сейчас (0 — нельзя)
    seen_price_kopecks: int | None

    @property
    def product(self) -> Product | None:
        return self.variant.product if self.variant else None

    @property
    def size(self) -> str | None:
        return self.variant.size if self.variant else None

    @property
    def unit_price_kopecks(self) -> int | None:
        return self.variant.product.price_kopecks if self.variant else None

    @property
    def line_total_kopecks(self) -> int:
        if self.status != LineStatus.OK:
            return 0
        return self.variant.product.price_kopecks * self.quantity

    @property
    def price_changed(self) -> bool:
        return (
            self.status != LineStatus.UNAVAILABLE
            and self.seen_price_kopecks is not None
            and self.seen_price_kopecks != self.unit_price_kopecks
        )


@dataclass(frozen=True)
class CartSummary:
    lines: list[CartLine] = field(default_factory=list)

    @property
    def total_kopecks(self) -> int:
        """Сумма только доступных позиций — ровно столько будет стоить заказ."""
        return sum(line.line_total_kopecks for line in self.lines)

    @property
    def items_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def has_problems(self) -> bool:
        return any(line.status != LineStatus.OK for line in self.lines)

    @property
    def can_checkout(self) -> bool:
        return bool(self.lines) and not self.has_problems

    @property
    def has_price_changes(self) -> bool:
        return any(line.price_changed for line in self.lines)


@dataclass(frozen=True)
class MergeNotice:
    variant_id: int
    reason: str  # значение MergeNoticeReason


@dataclass(frozen=True)
class MergeResult:
    summary: CartSummary
    notices: list[MergeNotice]


# --- Расчёт ---


def max_quantity(variant: ProductVariant) -> int:
    return min(variant.stock, settings.CART_MAX_QUANTITY)


def _load_variants(ids: Iterable[int]) -> dict[int, ProductVariant]:
    """Варианты вместе с удалёнными (чтобы показать, что именно стало недоступно).
    Видимость товара — тот же Product.objects.live(), что и на витрине."""
    queryset = (
        ProductVariant.all_objects.filter(pk__in=set(ids))
        .select_related("product")
        .prefetch_related("product__images")
        .annotate(product_is_live=Exists(Product.objects.live().filter(pk=OuterRef("product_id"))))
    )
    return {variant.pk: variant for variant in queryset}


def _status(variant: ProductVariant | None, quantity: int) -> tuple[str, int]:
    if variant is None or variant.deleted_at is not None or not variant.product_is_live:
        return LineStatus.UNAVAILABLE, 0
    limit = max_quantity(variant)
    if limit == 0:
        return LineStatus.OUT_OF_STOCK, 0
    if quantity > limit:
        return LineStatus.EXCEEDS_STOCK, limit
    return LineStatus.OK, limit


def _summarize(rows: list[tuple[int | None, LineInput]]) -> CartSummary:
    variants = _load_variants(line.variant_id for _, line in rows)
    lines = []
    for item_id, line in rows:
        variant = variants.get(line.variant_id)
        status, limit = _status(variant, line.quantity)
        lines.append(
            CartLine(
                id=item_id,
                variant_id=line.variant_id,
                variant=variant,
                quantity=line.quantity,
                status=status,
                max_quantity=limit,
                seen_price_kopecks=line.seen_price_kopecks,
            )
        )
    return CartSummary(lines)


def _normalize(lines: Iterable[LineInput]) -> list[LineInput]:
    """Дубли одного варианта схлопываются: количества складываются."""
    merged: dict[int, LineInput] = {}
    for line in lines:
        previous = merged.get(line.variant_id)
        if previous is None:
            merged[line.variant_id] = line
        else:
            merged[line.variant_id] = LineInput(
                variant_id=line.variant_id,
                quantity=previous.quantity + line.quantity,
                seen_price_kopecks=(
                    previous.seen_price_kopecks
                    if previous.seen_price_kopecks is not None
                    else line.seen_price_kopecks
                ),
            )
    return list(merged.values())


def get_summary(user) -> CartSummary:
    """Корзина клиента. Чтение корзину не создаёт."""
    rows = CartItem.objects.filter(cart__owner=user).values_list(
        "pk", "variant_id", "quantity", "seen_price_kopecks"
    )
    return _summarize(
        [(pk, LineInput(variant_id, quantity, seen)) for pk, variant_id, quantity, seen in rows]
    )


def quote(lines: Iterable[LineInput]) -> CartSummary:
    """Гостевая корзина с устройства: тот же расчёт без записи в БД."""
    lines = _normalize(lines)
    _check_items_limit(len(lines))
    return _summarize([(None, line) for line in lines])


# --- Изменение корзины клиента ---


def _check_items_limit(count: int) -> None:
    if count > settings.CART_MAX_ITEMS:
        raise ValidationError(
            f"В корзине может быть не больше {settings.CART_MAX_ITEMS} позиций.",
            code="cart_full",
        )


def _locked_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(owner=user)
    return Cart.objects.select_for_update().get(pk=cart.pk)


def _sellable_variant(variant_id: int) -> tuple[ProductVariant, int]:
    variant = _load_variants([variant_id]).get(variant_id)
    status, limit = _status(variant, 1)
    if status == LineStatus.UNAVAILABLE:
        raise ValidationError("Товар недоступен для заказа.", code="unavailable")
    if status == LineStatus.OUT_OF_STOCK:
        raise ValidationError("Товара нет в наличии.", code="out_of_stock")
    return variant, limit


def _owned_item(user, item_id: int) -> CartItem:
    item = (
        CartItem.objects.select_for_update(of=("self",))
        .filter(pk=item_id, cart__owner=user)
        .first()
    )
    if item is None:
        raise Http404("Позиция корзины не найдена.")
    return item


@transaction.atomic
def add(user, variant_id: int, quantity: int = 1) -> CartSummary:
    """Добавить вариант (или увеличить количество). Цена, которую видит покупатель
    в карточке товара, становится «увиденной»."""
    if quantity < 1:
        raise ValidationError("Количество должно быть не меньше 1.", code="invalid_quantity")
    cart = _locked_cart(user)
    variant, limit = _sellable_variant(variant_id)
    item = cart.items.filter(variant=variant).first()
    if item is None:
        _check_items_limit(cart.items.count() + 1)

    current = item.quantity if item else 0
    _check_addable(current, quantity, limit)

    price = variant.product.price_kopecks
    if item is None:
        CartItem.objects.create(
            cart=cart, variant=variant, quantity=quantity, seen_price_kopecks=price
        )
    else:
        item.quantity = current + quantity
        item.seen_price_kopecks = price
        item.save(update_fields=["quantity", "seen_price_kopecks"])
    return get_summary(user)


def _check_addable(current: int, quantity: int, limit: int) -> None:
    if current + quantity > limit:
        already = f" В корзине уже {current}." if current else ""
        raise ValidationError(
            f"Можно добавить не больше {limit} шт.{already}", code="quantity_limit"
        )


def _check_quantity(quantity: int, limit: int) -> None:
    if not 1 <= quantity <= limit:
        raise ValidationError(f"Укажите количество от 1 до {limit}.", code="quantity_limit")


@transaction.atomic
def set_quantity(user, item_id: int, quantity: int) -> CartSummary:
    item = _owned_item(user, item_id)
    _, limit = _sellable_variant(item.variant_id)
    _check_quantity(quantity, limit)
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    return get_summary(user)


def remove(user, item_id: int) -> CartSummary:
    deleted, _ = CartItem.objects.filter(pk=item_id, cart__owner=user).delete()
    if not deleted:
        raise Http404("Позиция корзины не найдена.")
    return get_summary(user)


def ack_prices(user) -> CartSummary:
    """Покупатель увидел новые цены: предупреждение «цена изменилась» снимается."""
    current_price = ProductVariant.all_objects.filter(pk=OuterRef("variant_id")).values(
        "product__price_kopecks"
    )[:1]
    CartItem.objects.filter(cart__owner=user).update(seen_price_kopecks=Subquery(current_price))
    return get_summary(user)


@transaction.atomic
def merge(user, lines: Iterable[LineInput]) -> MergeResult:
    """Перенос гостевой корзины после входа или регистрации.

    Количества складываются и ограничиваются доступным; недоступные позиции и позиции
    сверх лимита корзины пропускаются — о них сообщают notices.
    """
    LIMITED = MergeNoticeReason.QUANTITY_LIMITED.value
    lines = _normalize(lines)
    cart = _locked_cart(user)
    existing = {item.variant_id: item for item in cart.items.all()}
    variants = _load_variants(line.variant_id for line in lines)
    notices: list[MergeNotice] = []
    count = len(existing)

    for line in lines:
        variant = variants.get(line.variant_id)
        status, limit = _status(variant, 1)
        if status != LineStatus.OK:
            notices.append(MergeNotice(line.variant_id, str(status)))
            continue

        item = existing.get(variant.pk)
        if item is not None:
            wanted = item.quantity + line.quantity
            new_quantity = min(wanted, limit)
            if new_quantity < wanted:
                notices.append(MergeNotice(variant.pk, LIMITED))
            if new_quantity > item.quantity:
                item.quantity = new_quantity
                item.save(update_fields=["quantity"])
            continue

        if count >= settings.CART_MAX_ITEMS:
            notices.append(MergeNotice(variant.pk, MergeNoticeReason.CART_FULL.value))
            continue
        quantity = min(line.quantity, limit)
        if quantity < line.quantity:
            notices.append(MergeNotice(variant.pk, LIMITED))
        seen = line.seen_price_kopecks
        CartItem.objects.create(
            cart=cart,
            variant=variant,
            quantity=quantity,
            seen_price_kopecks=seen if seen is not None else variant.product.price_kopecks,
        )
        count += 1

    return MergeResult(get_summary(user), notices)


# --- Гостевая корзина: те же правила, позиции хранит вызывающий (сессия сайта) ---


def guest_add(lines: Iterable[LineInput], variant_id: int, quantity: int = 1) -> list[LineInput]:
    """Как add(): товар продаётся, количество не больше доступного, позиций не больше лимита.
    Возвращает новый список позиций; «увиденная» цена — текущая цена товара."""
    if quantity < 1:
        raise ValidationError("Количество должно быть не меньше 1.", code="invalid_quantity")
    lines = _normalize(lines)
    variant, limit = _sellable_variant(variant_id)
    current = next((line for line in lines if line.variant_id == variant.pk), None)
    if current is None:
        _check_items_limit(len(lines) + 1)
    _check_addable(current.quantity if current else 0, quantity, limit)
    price = variant.product.price_kopecks
    if current is None:
        return [*lines, LineInput(variant.pk, quantity, price)]
    updated = LineInput(variant.pk, current.quantity + quantity, price)
    return [updated if line.variant_id == variant.pk else line for line in lines]


def guest_set_quantity(
    lines: Iterable[LineInput], variant_id: int, quantity: int
) -> list[LineInput]:
    lines = _normalize(lines)
    if not any(line.variant_id == variant_id for line in lines):
        raise Http404("Позиция корзины не найдена.")
    _, limit = _sellable_variant(variant_id)
    _check_quantity(quantity, limit)
    return [
        replace(line, quantity=quantity) if line.variant_id == variant_id else line
        for line in lines
    ]


def guest_remove(lines: Iterable[LineInput], variant_id: int) -> list[LineInput]:
    lines = _normalize(lines)
    remaining = [line for line in lines if line.variant_id != variant_id]
    if len(remaining) == len(lines):
        raise Http404("Позиция корзины не найдена.")
    return remaining


def guest_ack_prices(lines: Iterable[LineInput]) -> list[LineInput]:
    """Предупреждение «цена изменилась» снимается: увиденная цена = текущая."""
    lines = _normalize(lines)
    variants = _load_variants(line.variant_id for line in lines)
    return [
        replace(line, seen_price_kopecks=variants[line.variant_id].product.price_kopecks)
        if line.variant_id in variants
        else line
        for line in lines
    ]
