"""Журнал просмотров покупателя («Вы смотрели» в профиле).

Пишется при открытии карточки товара вошедшим покупателем (сайт; приложение — через API).
Одна строка на пару «покупатель + товар»: повторный просмотр только обновляет время.
Хранятся последние HISTORY_LIMIT товаров; администраторы и гости не пишутся.
"""

from django.utils import timezone

from store.models import Product, ProductView
from store.services.storefront import live_products

HISTORY_LIMIT = 30


def _is_customer(user) -> bool:
    return bool(user and user.is_authenticated and not user.is_staff)


def record_view(user, product: Product) -> None:
    if not _is_customer(user):
        return
    # Upsert одним запросом: параллельные вкладки не ломают уникальность.
    ProductView.objects.bulk_create(
        [ProductView(user=user, product=product, viewed_at=timezone.now())],
        update_conflicts=True,
        unique_fields=["user", "product"],
        update_fields=["viewed_at"],
    )
    newest = ProductView.objects.filter(user=user).order_by("-viewed_at", "-id")
    ProductView.objects.filter(user=user).exclude(
        pk__in=newest.values("pk")[:HISTORY_LIMIT]
    ).delete()


def recent_products(user, limit: int = 12) -> list[Product]:
    """Недавно просмотренные товары, видимые на витрине, — от последнего к первому."""
    if not _is_customer(user):
        return []
    ids = list(
        ProductView.objects.filter(user=user)
        .order_by("-viewed_at", "-id")
        .values_list("product_id", flat=True)[:limit]
    )
    if not ids:
        return []
    found = {product.pk: product for product in live_products().filter(pk__in=ids)}
    return [found[pk] for pk in ids if pk in found]


def clear(user) -> None:
    if _is_customer(user):
        ProductView.objects.filter(user=user).delete()
