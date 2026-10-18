"""Генератор демо-каталога: fixtures/catalog.json и fixtures/demo_images/manifest.json.

    python3 scripts/demo_catalog.py

Фото скачивает scripts/fetch_demo_images.py (нужен интернет), к товарам их привязывает
`manage.py seed_demo`. Цены — целые копейки.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# pk, name, slug, parent, position
CATEGORIES = [
    (1, "Аксессуары", "aksessuary", None, 0),
    (2, "Одежда", "odezhda", None, 1),
    (4, "Обувь", "obuv", None, 2),
    (3, "Красота и здоровье", "krasota-i-zdorove", None, 3),
    (5, "Часы", "chasy", 1, 0),
    (6, "Очки", "ochki", 1, 1),
    (12, "Сумки и рюкзаки", "sumki", 1, 2),
    (9, "Футболки", "futbolki", 2, 0),
    (13, "Худи и свитшоты", "hudi", 2, 1),
    (11, "Кроссовки и кеды", "krossovki", 4, 0),
    (10, "Зимняя обувь", "zimnie", 4, 1),
    (8, "Косметика", "kosmetika", 3, 0),
    (7, "Витамины", "vitaminy", 3, 1),
]

CLOTHES = ("S", "M", "L")
SHOES = ("39", "40", "41", "42")
NO_SIZE = ("",)

# pk, category, name, slug, description, price ₽, old price ₽, sizes, stock, photo queries
PRODUCTS = [
    (
        1,
        5,
        "Часы-хронограф «Навигатор»",
        "chasy-hronograf-navigator",
        "Хронограф со стальным корпусом 42 мм и коричневым кожаным ремешком. "
        "Кварцевый механизм, сапфировое покрытие стекла, водозащита 5 ATM.",
        12_990,
        None,
        NO_SIZE,
        10,
        ["chronograph watch leather strap", "wristwatch closeup"],
    ),
    (
        2,
        5,
        "Часы «Классика» серебристые",
        "chasy-klassika-serebristye",
        "Лаконичные кварцевые часы на стальном браслете. Подходят и к костюму, и к свитеру.",
        8_490,
        None,
        NO_SIZE,
        10,
        ["silver analog watch"],
    ),
    (
        3,
        5,
        "Часы «Полночь» чёрные",
        "chasy-polnoch-chernye",
        "Матовый чёрный корпус, светящиеся стрелки, силиконовый ремешок. Водозащита 10 ATM.",
        10_990,
        13_990,
        NO_SIZE,
        3,
        ["black wrist watch"],
    ),
    (
        4,
        6,
        "Солнцезащитные очки «Авиатор»",
        "ochki-aviator",
        "Металлическая оправа, поляризованные линзы с защитой UV400. В комплекте футляр.",
        4_990,
        None,
        NO_SIZE,
        10,
        ["aviator sunglasses"],
    ),
    (
        5,
        6,
        "Очки «Вэйфарер» чёрные",
        "ochki-veyfarer",
        "Классическая форма в ацетатной оправе. Линзы UV400, подходят для вождения.",
        3_790,
        4_990,
        NO_SIZE,
        10,
        ["black sunglasses"],
    ),
    (
        6,
        6,
        "Очки «Ретро» круглые",
        "ochki-retro-kruglye",
        "Тонкая круглая оправа и тёмные линзы — образ в стиле 70-х.",
        3_290,
        None,
        NO_SIZE,
        10,
        ["round sunglasses"],
    ),
    (
        7,
        12,
        "Сумка-тоут из натуральной кожи",
        "sumka-tout",
        'Вместительная сумка на каждый день: ноутбук 14", внутренний карман на молнии.',
        6_990,
        None,
        NO_SIZE,
        5,
        ["leather tote bag", "leather handbag"],
    ),
    (
        8,
        12,
        "Рюкзак городской",
        "ryukzak-gorodskoy",
        'Водоотталкивающая ткань, отделение для ноутбука 15", объём 20 л.',
        4_490,
        None,
        NO_SIZE,
        10,
        ["backpack"],
    ),
    (
        9,
        9,
        "Футболка базовая белая",
        "futbolka-bazovaya-belaya",
        "Плотный хлопок 180 г/м², прямой крой. Не просвечивает и не садится после стирки.",
        1_490,
        None,
        CLOTHES,
        10,
        ["white t-shirt"],
    ),
    (
        10,
        9,
        "Футболка оверсайз чёрная",
        "futbolka-oversayz-chernaya",
        "Свободный крой, спущенное плечо, 100% хлопок.",
        1_990,
        None,
        CLOTHES,
        10,
        ["black t-shirt"],
    ),
    (
        11,
        9,
        "Футболка с принтом «Горы»",
        "futbolka-gory",
        "Мягкий хлопок и стойкий принт, который не трескается после стирок.",
        2_290,
        2_790,
        CLOTHES,
        10,
        ["graphic t-shirt"],
    ),
    (
        12,
        13,
        "Худи оверсайз серое",
        "hudi-oversayz-seroe",
        "Тёплый футер с начёсом, капюшон на кулиске, карман-кенгуру.",
        3_490,
        None,
        CLOTHES,
        10,
        ["grey hoodie", "hoodie"],
    ),
    (
        13,
        13,
        "Свитшот бежевый",
        "svitshot-bezhevyy",
        "Хлопковый свитшот с мягким начёсом. Базовая вещь на межсезонье.",
        2_990,
        None,
        CLOTHES,
        10,
        ["sweatshirt"],
    ),
    (
        14,
        13,
        "Худи на молнии чёрное",
        "hudi-na-molnii-chernoe",
        "Двусторонняя молния, плотный трикотаж. Временно нет в наличии.",
        3_990,
        4_590,
        CLOTHES,
        0,
        ["black hoodie"],
    ),
    (
        15,
        11,
        "Кроссовки беговые «Спринт»",
        "krossovki-sprint",
        "Лёгкая сетка, амортизирующая подошва. Для бега и на каждый день.",
        7_990,
        None,
        SHOES,
        10,
        ["running sneakers", "sneakers"],
    ),
    (
        16,
        11,
        "Кеды белые классические",
        "kedy-belye",
        "Кожаный верх, резиновая подошва. Сочетаются с чем угодно.",
        5_490,
        None,
        SHOES,
        10,
        ["white sneakers"],
    ),
    (
        17,
        11,
        "Кроссовки «Стрит» яркие",
        "krossovki-strit",
        "Смелые цвета, высокая подошва, мягкая стелька.",
        8_990,
        10_990,
        SHOES,
        2,
        ["colorful sneakers"],
    ),
    (
        18,
        10,
        "Ботинки зимние «Тайга»",
        "botinki-tayga",
        "Натуральный мех внутри, нескользящая подошва, держат до −30 °C.",
        11_990,
        None,
        SHOES,
        10,
        ["winter boots"],
    ),
    (
        19,
        10,
        "Угги замшевые",
        "uggi-zamshevye",
        "Овчина внутри и снаружи — тепло и мягко.",
        8_490,
        None,
        SHOES,
        10,
        ["suede boots"],
    ),
    (
        20,
        10,
        "Челси утеплённые",
        "chelsi-uteplennye",
        "Кожаные челси с шерстяной подкладкой и эластичными вставками.",
        9_790,
        None,
        SHOES,
        10,
        ["chelsea boots"],
    ),
    (
        21,
        8,
        "Крем для лица увлажняющий",
        "krem-dlya-lica",
        "Гиалуроновая кислота и сквалан. Для всех типов кожи, 50 мл.",
        1_290,
        None,
        NO_SIZE,
        10,
        ["face cream jar"],
    ),
    (
        22,
        8,
        "Сыворотка с витамином C",
        "syvorotka-vitamin-c",
        "Выравнивает тон и придаёт сияние. Флакон с пипеткой, 30 мл.",
        1_890,
        2_290,
        NO_SIZE,
        10,
        ["serum bottle dropper"],
    ),
    (
        23,
        8,
        "Помада матовая",
        "pomada-matovaya",
        "Стойкий матовый финиш, не сушит губы.",
        890,
        None,
        NO_SIZE,
        10,
        ["lipstick"],
    ),
    (
        24,
        7,
        "Витамин D3 2000 МЕ",
        "vitamin-d3",
        "120 капсул — запас на 4 месяца. Не является лекарственным средством.",
        690,
        None,
        NO_SIZE,
        10,
        ["vitamin supplement bottle"],
    ),
    (
        25,
        7,
        "Омега-3 рыбий жир",
        "omega-3",
        "Капсулы 1000 мг. Не является лекарственным средством.",
        1_290,
        None,
        NO_SIZE,
        10,
        ["fish oil capsules"],
    ),
]

START = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def build():
    objects = []
    for pk, name, slug, parent, position in CATEGORIES:
        objects.append(
            {
                "model": "store.category",
                "pk": pk,
                "fields": {
                    "name": name,
                    "slug": slug,
                    "parent": parent,
                    "position": position,
                    "is_active": True,
                    "created_at": iso(START),
                    "updated_at": iso(START),
                },
            }
        )

    manifest = []
    variant_pk = 0
    for index, (
        pk,
        category,
        name,
        slug,
        description,
        price,
        old,
        sizes,
        stock,
        photos,
    ) in enumerate(PRODUCTS):
        created = iso(START + timedelta(hours=index))
        objects.append(
            {
                "model": "store.product",
                "pk": pk,
                "fields": {
                    "name": name,
                    "slug": slug,
                    "description": description,
                    "category": category,
                    "price_kopecks": price * 100,
                    "compare_at_kopecks": old * 100 if old else None,
                    "is_active": True,
                    "created_at": created,
                    "updated_at": created,
                    "deleted_at": None,
                },
            }
        )
        for position, size in enumerate(sizes):
            variant_pk += 1
            objects.append(
                {
                    "model": "store.productvariant",
                    "pk": variant_pk,
                    "fields": {
                        "product": pk,
                        "size": size,
                        "sku": f"DD-{pk}-{size}" if size else f"DD-{pk}",
                        "stock": stock,
                        "position": position,
                        "created_at": created,
                        "updated_at": created,
                        "deleted_at": None,
                    },
                }
            )
        manifest.append(
            {
                "slug": slug,
                "images": [
                    {"file": f"{slug}-{n + 1}.jpg", "query": query}
                    for n, query in enumerate(photos)
                ],
            }
        )

    (ROOT / "fixtures/catalog.json").write_text(
        json.dumps(objects, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    images_dir = ROOT / "fixtures/demo_images"
    images_dir.mkdir(exist_ok=True)
    (images_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
