"""Корзина витрины: одна точка входа для гостя и клиента.

Гость — позиции в серверной сессии Django (работает без JavaScript), правила те же, что у
корзины в БД (store.services.cart.guest_*). Клиент — корзина в БД. При входе гостевая корзина
переносится в корзину аккаунта через cart.merge и из сессии удаляется.
"""

from django.db.models import Sum

from store.models import CartItem, ProductVariant
from store.services import cart as cart_service
from store.services.cart import CartSummary, LineInput, MergeNotice

SESSION_KEY = "cart"


def _is_customer(request) -> bool:
    return request.user.is_authenticated


# --- Хранение гостевой корзины в сессии ---


def _read_session(request) -> list[LineInput]:
    raw = request.session.get(SESSION_KEY) or []
    lines = []
    for row in raw:
        try:
            variant_id, quantity, seen = int(row[0]), int(row[1]), row[2]
        except (TypeError, ValueError, IndexError):
            continue  # повреждённая запись — пропускаем, а не роняем страницу
        if variant_id > 0 and quantity > 0:
            lines.append(LineInput(variant_id, quantity, int(seen) if seen is not None else None))
    return lines


def _write_session(request, lines: list[LineInput]) -> None:
    if lines:
        request.session[SESSION_KEY] = [
            [line.variant_id, line.quantity, line.seen_price_kopecks] for line in lines
        ]
    else:
        request.session.pop(SESSION_KEY, None)


# --- Операции ---


def summary(request) -> CartSummary:
    if _is_customer(request):
        return cart_service.get_summary(request.user)
    return cart_service.quote(_read_session(request))


def count(request) -> int:
    """Число единиц для значка в шапке: один лёгкий запрос, без расчёта корзины."""
    if _is_customer(request):
        total = CartItem.objects.filter(cart__owner=request.user).aggregate(n=Sum("quantity"))["n"]
        return total or 0
    if SESSION_KEY not in getattr(request, "session", {}):
        return 0
    return sum(line.quantity for line in _read_session(request))


def quantities(request) -> dict[int, int]:
    """Сколько единиц каждого товара в корзине: {product_id: штук} — для значка «В корзине»."""
    if _is_customer(request):
        rows = (
            CartItem.objects.filter(cart__owner=request.user)
            .values("variant__product_id")
            .annotate(n=Sum("quantity"))
            .values_list("variant__product_id", "n")
        )
        return dict(rows)
    if SESSION_KEY not in getattr(request, "session", {}):
        return {}
    lines = _read_session(request)
    products = dict(
        ProductVariant.all_objects.filter(pk__in=[line.variant_id for line in lines]).values_list(
            "pk", "product_id"
        )
    )
    result: dict[int, int] = {}
    for line in lines:
        if line.variant_id in products:
            product_id = products[line.variant_id]
            result[product_id] = result.get(product_id, 0) + line.quantity
    return result


def variant_quantities(request, variant_ids) -> dict[int, int]:
    """Сколько штук каждого размера уже в корзине: {variant_id: штук} — для карточки товара."""
    ids = set(variant_ids)
    if _is_customer(request):
        rows = CartItem.objects.filter(cart__owner=request.user, variant_id__in=ids)
        return dict(rows.values_list("variant_id", "quantity"))
    if SESSION_KEY not in getattr(request, "session", {}):
        return {}
    return {
        line.variant_id: line.quantity for line in _read_session(request) if line.variant_id in ids
    }


def product_slugs(request) -> list[str]:
    """Slug товаров в корзине (один запрос): сетки товаров общие для всех (кэш), метку
    «В корзине» на карточки ставит site.js."""
    if _is_customer(request):
        items = CartItem.objects.filter(cart__owner=request.user)
        return list(items.values_list("variant__product__slug", flat=True).distinct())
    if SESSION_KEY not in getattr(request, "session", {}):
        return []
    ids = [line.variant_id for line in _read_session(request)]
    variants = ProductVariant.all_objects.filter(pk__in=ids)
    return list(variants.values_list("product__slug", flat=True).distinct())


def add(request, variant_id: int, quantity: int = 1) -> None:
    if _is_customer(request):
        cart_service.add(request.user, variant_id, quantity)
    else:
        _write_session(
            request, cart_service.guest_add(_read_session(request), variant_id, quantity)
        )


def set_quantity(request, variant_id: int, quantity: int) -> None:
    if _is_customer(request):
        item_id = _item_id(request.user, variant_id)
        cart_service.set_quantity(request.user, item_id, quantity)
    else:
        _write_session(
            request, cart_service.guest_set_quantity(_read_session(request), variant_id, quantity)
        )


def remove(request, variant_id: int) -> None:
    if _is_customer(request):
        cart_service.remove(request.user, _item_id(request.user, variant_id))
    else:
        _write_session(request, cart_service.guest_remove(_read_session(request), variant_id))


def ack_prices(request) -> None:
    if _is_customer(request):
        cart_service.ack_prices(request.user)
    else:
        _write_session(request, cart_service.guest_ack_prices(_read_session(request)))


def take_guest_lines(request) -> list[LineInput]:
    """Позиции гостя до входа: вызывать до login() — после него request.user уже клиент."""
    return _read_session(request)


def merge_into_account(request, lines: list[LineInput]) -> list[MergeNotice]:
    """После входа или регистрации: гостевая корзина → корзина аккаунта."""
    request.session.pop(SESSION_KEY, None)
    if not lines:
        return []
    return cart_service.merge(request.user, lines).notices


def _item_id(user, variant_id: int) -> int:
    item_id = (
        CartItem.objects.filter(cart__owner=user, variant_id=variant_id)
        .values_list("pk", flat=True)
        .first()
    )
    # Несуществующая позиция: тот же Http404, что у сервиса для чужой позиции.
    return item_id if item_id is not None else 0
