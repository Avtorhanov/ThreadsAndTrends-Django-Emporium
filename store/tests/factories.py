"""Фабрики тестовых данных каталога (общие для тестов store, orders, core)."""

from itertools import count

from store.models import Category, Product, ProductVariant

_seq = count(1)


def make_category(name="Одежда", parent=None, **fields) -> Category:
    n = next(_seq)
    fields.setdefault("slug", f"category-{n}")
    return Category.objects.create(name=name, parent=parent, **fields)


def make_product(
    name="Футболка",
    category=None,
    price_kopecks=100_00,
    stock=5,
    sizes=("",),
    **fields,
) -> Product:
    n = next(_seq)
    fields.setdefault("slug", f"product-{n}")
    fields.setdefault("description", "Описание")
    product = Product.objects.create(
        name=name,
        category=category or make_category(),
        price_kopecks=price_kopecks,
        **fields,
    )
    for position, size in enumerate(sizes):
        ProductVariant.objects.create(
            product=product,
            size=size,
            sku=f"SKU-{n}-{position}",
            stock=stock,
            position=position,
        )
    return product
