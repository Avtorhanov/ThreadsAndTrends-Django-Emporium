"""Категории превью на GitHub Pages: плоский список как в каналах магазина.

Применяется только в deploy/preview/build.py после `seed_demo`: фикстуры и боевая БД не меняются.
Демо-товары переносятся в новые категории по slug, старое дерево удаляется. «В наличии» —
товары, которые уже лежат на месте и отправляются сразу; остальное — под заказ. Остаток
(есть / нет в наличии) у вариантов работает как раньше, независимо от категории.
"""

from django.db import transaction

from store.models import Category, Product
from store.services import catalog

# slug, название (порядок в списке = порядок в меню)
CATEGORIES = [
    ("muzhskoe", "Мужское"),
    ("zhenskoe", "Женское"),
    ("detskoe", "Детское"),
    ("zdorove-krasota-vkusnyashki", "Здоровье/красота/вкусняшки"),
    ("luxe", "LUXE"),
    ("dlya-doma", "Для дома"),
    ("v-nalichii", "В наличии"),
]

# slug категории → slug демо-товаров из fixtures/catalog.json
PRODUCTS = {
    "muzhskoe": [
        "ochki-aviator",
        "ryukzak-gorodskoy",
        "hudi-na-molnii-chernoe",
        "krossovki-sprint",
        "botinki-tayga",
        "chelsi-uteplennye",
    ],
    "zhenskoe": [
        "chasy-klassika-serebristye",
        "ochki-retro-kruglye",
        "futbolka-bazovaya-belaya",
        "svitshot-bezhevyy",
        "uggi-zamshevye",
    ],
    "detskoe": ["futbolka-gory", "hudi-oversayz-seroe", "krossovki-strit"],
    "zdorove-krasota-vkusnyashki": [
        "krem-dlya-lica",
        "syvorotka-vitamin-c",
        "pomada-matovaya",
        "vitamin-d3",
        "omega-3",
    ],
    "luxe": ["chasy-hronograf-navigator", "ochki-veyfarer", "sumka-tout"],
    "v-nalichii": ["chasy-polnoch-chernye", "futbolka-oversayz-chernaya", "kedy-belye"],
}

# Новые демо-товары «Для дома» (фото нет — карточка покажет заглушку). Цены — копейки.
HOME_PRODUCTS = [
    {
        "name": "Термокружка стальная 470 мл",
        "slug": "termokruzhka-stalnaya-470",
        "description": "Двойные стенки из нержавеющей стали: горячее держит 6 часов, "
        "холодное — 12. Герметичная крышка, подходит под автомобильный подстаканник.",
        "price_kopecks": 249_000,
        "compare_at_kopecks": 299_000,
        "stock": 8,
    },
    {
        "name": "Трубочки многоразовые, набор 4 шт.",
        "slug": "trubochki-mnogorazovye-nabor",
        "description": "Стальные трубочки для холодных напитков и смузи, ёршик для мытья "
        "и чехол в комплекте. Можно мыть в посудомоечной машине.",
        "price_kopecks": 170_000,
        "compare_at_kopecks": None,
        "stock": 12,
    },
    {
        "name": "Плед вязаный «Уют»",
        "slug": "pled-vyazanyy-uyut",
        "description": "Крупная вязка, 130×170 см, мягкая акриловая пряжа. Не линяет "
        "и не скатывается после стирки.",
        "price_kopecks": 399_000,
        "compare_at_kopecks": None,
        "stock": 0,  # показывает состояние «Нет в наличии»
    },
]


@transaction.atomic
def apply() -> None:
    old = list(Category.objects.all())
    new = {
        slug: catalog.create_category(name=name, slug=slug, position=position)
        for position, (slug, name) in enumerate(CATEGORIES)
    }

    for category_slug, product_slugs in PRODUCTS.items():
        moved = Product.all_objects.filter(slug__in=product_slugs).update(
            category=new[category_slug]
        )
        # Опечатка в slug иначе молча оставит товар в старой категории и сломает удаление ниже.
        assert moved == len(product_slugs), (category_slug, moved, len(product_slugs))

    for item in HOME_PRODUCTS:
        catalog.create_product(
            name=item["name"],
            slug=item["slug"],
            description=item["description"],
            category=new["dlya-doma"],
            price_kopecks=item["price_kopecks"],
            compare_at_kopecks=item["compare_at_kopecks"],
            variants=[{"size": "", "stock": item["stock"]}],
        )

    # Сначала подкатегории, потом корни: parent — PROTECT.
    for category in sorted(old, key=lambda c: c.parent_id is None):
        catalog.delete_category(category)
