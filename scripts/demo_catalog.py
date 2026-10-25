"""Генератор демо-каталога: fixtures/catalog.json и fixtures/demo_images/manifest.json.

    python3 scripts/demo_catalog.py

Категории — плоский список, как каналы магазина. Товары — посты поставщика (фото поставщика
лежат в fixtures/demo_images, в манифесте помечены "source": "supplier"); «Женское» — прежние
демо-товары с фото из открытых источников (их загружает scripts/fetch_demo_images.py, поля
"pick" и "queries" в манифесте сохраняются). Фото к товарам привязывает `manage.py seed_demo`.
Цены — целые копейки; цена None — «цена по запросу».
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "fixtures/demo_images/manifest.json"

# pk, name, slug (порядок списка = порядок в меню)
CATEGORIES = [
    (1, "Мужское", "muzhskoe"),
    (2, "Женское", "zhenskoe"),
    (3, "Детское", "detskoe"),
    (4, "Здоровье/красота/вкусняшки", "zdorove-krasota-vkusnyashki"),
    (5, "LUXE", "luxe"),
    (6, "Для дома", "dlya-doma"),
    (7, "В наличии", "v-nalichii"),
]

MEN = ("S", "M", "L", "XL")
WOMEN = ("S", "M", "L")
WOMEN_SHOES = ("37", "38", "39", "40")
KIDS_HEIGHT = ("116", "122", "128", "134", "140", "146", "152", "158", "164")
KIDS_SHOES = ("28", "29", "30", "31", "32", "33", "34", "35")
NO_SIZE = ("",)

ON_ORDER = "Под заказ: привезём из США."
NOT_A_DRUG = "Не является лекарственным средством."
ASK_LUXE = "Цену, размер и сроки уточните у продавца — кнопка «Узнать»."
IN_STOCK = "Уже у нас — отправим сразу."


def supplier(slug: str, post: str, count: int = 1) -> list[dict]:
    """Фото из поста поставщика: <slug>-1.jpg … (обрезаны до самого снимка)."""
    return [
        {"file": f"{slug}-{n}.jpg", "source": "supplier", "post": post} for n in range(1, count + 1)
    ]


KEEP = None  # фото из текущего манифеста (открытые источники, закреплённые "pick")

# pk, категория, название, slug, описание, цена ₽ (None — по запросу), старая цена ₽,
# размеры, остаток каждого размера, фото
PRODUCTS = [
    # --- Мужское (U.S. Polo Assn.) ---
    (
        1,
        1,
        "U.S. Polo Assn. — лонгслив, зелёный / бежевый",
        "us-polo-longsliv-zelenyy-bezhevyy",
        "Лонгслив с круглым вырезом и вышитым логотипом. Цвета: зелёный и бежевый — "
        f"укажите цвет в комментарии к заказу. {ON_ORDER}",
        1_900,
        None,
        MEN,
        10,
        supplier("us-polo-longsliv-zelenyy-bezhevyy", "811727"),
    ),
    (
        2,
        1,
        "U.S. Polo Assn. — лонгслив, синий / серый / белый",
        "us-polo-longsliv-siniy-seryy-belyy",
        "Лонгслив с круглым вырезом и вышитым логотипом. Цвета: синий, серый и белый — "
        f"укажите цвет в комментарии к заказу. {ON_ORDER}",
        1_900,
        None,
        MEN,
        10,
        supplier("us-polo-longsliv-siniy-seryy-belyy", "811726"),
    ),
    (
        3,
        1,
        "U.S. Polo Assn. — поло трикотажное",
        "us-polo-polo-trikotazhnoe",
        "Трикотажное поло с открытым воротником и контрастной отделкой. Цвета: чёрный, "
        f"молочный и зелёный — укажите цвет в комментарии к заказу. {ON_ORDER}",
        3_200,
        None,
        MEN,
        10,
        supplier("us-polo-polo-trikotazhnoe", "811724"),
    ),
    (
        4,
        1,
        "U.S. Polo Assn. — футболка",
        "us-polo-futbolka",
        "Базовая футболка с вышитым логотипом. Цвета: сиреневый, жёлтый, коричневый, "
        f"голубой и мятный — укажите цвет в комментарии к заказу. {ON_ORDER}",
        1_200,
        None,
        MEN,
        10,
        supplier("us-polo-futbolka", "811723"),
    ),
    # --- Женское (прежние демо-товары) ---
    (
        5,
        2,
        "Часы «Классика» серебристые",
        "chasy-klassika-serebristye",
        "Лаконичные кварцевые часы на стальном браслете. Подходят и к костюму, и к свитеру.",
        8_490,
        None,
        NO_SIZE,
        10,
        KEEP,
    ),
    (
        6,
        2,
        "Очки «Ретро» круглые",
        "ochki-retro-kruglye",
        "Тонкая круглая оправа и тёмные линзы — образ в стиле 70-х.",
        3_290,
        None,
        NO_SIZE,
        10,
        KEEP,
    ),
    (
        7,
        2,
        "Футболка базовая белая",
        "futbolka-bazovaya-belaya",
        "Плотный хлопок 180 г/м², прямой крой. Не просвечивает и не садится после стирки.",
        1_490,
        None,
        WOMEN,
        10,
        KEEP,
    ),
    (
        8,
        2,
        "Свитшот бежевый",
        "svitshot-bezhevyy",
        "Хлопковый свитшот с мягким начёсом. Базовая вещь на межсезонье.",
        2_990,
        None,
        WOMEN,
        10,
        KEEP,
    ),
    (
        9,
        2,
        "Угги замшевые",
        "uggi-zamshevye",
        "Овчина внутри и снаружи — тепло и мягко.",
        8_490,
        None,
        WOMEN_SHOES,
        10,
        KEEP,
    ),
    # --- Детское ---
    (
        10,
        3,
        "Lefties — пижама для девочек «Печеньки» / «Вишни»",
        "lefties-pizhama-pechenki-vishni",
        "Пижама из лонгслива и брюк на манжетах. Два принта — печеньки (голубая) и вишни "
        "(розовая): укажите принт в комментарии к заказу. Размер — по росту, 116–164 см. "
        "Под заказ из Испании.",
        1_600,
        None,
        KIDS_HEIGHT,
        10,
        supplier("lefties-pizhama-pechenki-vishni", "805079"),
    ),
    (
        11,
        3,
        "Lefties — пижама для девочек в полоску",
        "lefties-pizhama-poloska",
        "Пижама в тонкую полоску с вышивкой и волнистым краем. Размер — по росту, 116–164 см. "
        "Под заказ из Испании.",
        2_100,
        None,
        KIDS_HEIGHT,
        10,
        supplier("lefties-pizhama-poloska", "805079"),
    ),
    (
        12,
        3,
        "New Balance — кроссовки детские",
        "new-balance-krossovki-detskie",
        f"Беговые кроссовки для детей, линейка Little Kids, шнурки с фиксатором. {ON_ORDER}",
        4_500,
        None,
        KIDS_SHOES,
        10,
        supplier("new-balance-krossovki-detskie", "809345"),
    ),
    # --- Здоровье/красота/вкусняшки ---
    (
        13,
        4,
        "Thorne Basic Nutrients 2/Day — 60 капсул",
        "thorne-basic-nutrients-60",
        f"Комплексный мультивитамин, 2 капсулы в день. 60 капсул. {ON_ORDER} {NOT_A_DRUG}",
        4_400,
        None,
        NO_SIZE,
        10,
        supplier("thorne-basic-nutrients-60", "806967"),
    ),
    (
        14,
        4,
        "Thorne Basic Nutrients 2/Day — 120 капсул",
        "thorne-basic-nutrients-120",
        f"Комплексный мультивитамин, 2 капсулы в день. 120 капсул. {ON_ORDER} {NOT_A_DRUG}",
        8_200,
        None,
        NO_SIZE,
        10,
        supplier("thorne-basic-nutrients-120", "806967"),
    ),
    (
        15,
        4,
        "Life Extension Two-Per-Day — 60 таблеток",
        "life-extension-two-per-day-60",
        f"Мультивитамины и минералы, 2 таблетки в день. 60 таблеток. {ON_ORDER} {NOT_A_DRUG}",
        1_300,
        None,
        NO_SIZE,
        10,
        supplier("life-extension-two-per-day-60", "807053"),
    ),
    (
        16,
        4,
        "Life Extension Two-Per-Day — 120 таблеток",
        "life-extension-two-per-day-120",
        f"Мультивитамины и минералы, 2 таблетки в день. 120 таблеток. {ON_ORDER} {NOT_A_DRUG}",
        2_300,
        None,
        NO_SIZE,
        10,
        supplier("life-extension-two-per-day-120", "807053"),
    ),
    (
        17,
        4,
        "Kinder — адвент-календарь Classic",
        "kinder-advent-classic",
        "24 окошка со сладостями Kinder, hanuta, duplo и другими, 295 г. Под заказ из Германии.",
        2_400,
        None,
        NO_SIZE,
        10,
        supplier("kinder-advent-classic", "810528"),
    ),
    (
        18,
        4,
        "Kinder — адвент-календарь «Домик»",
        "kinder-advent-domik",
        "Календарь-домик с 24 окошками, шоколад Kinder, 351 г. Под заказ из Германии.",
        2_900,
        None,
        NO_SIZE,
        10,
        supplier("kinder-advent-domik", "810532"),
    ),
    # --- LUXE: цена по запросу ---
    (
        19,
        5,
        "Gucci — лоферы замшевые Horsebit",
        "gucci-lofery-horsebit",
        f"Замшевые лоферы с тиснением GG и металлической пряжкой Horsebit. {ASK_LUXE}",
        None,
        None,
        NO_SIZE,
        1,
        supplier("gucci-lofery-horsebit", "luxe"),
    ),
    (
        20,
        5,
        "Gucci — слингбэки GG Horsebit",
        "gucci-slingbek-horsebit",
        f"Туфли-слингбэки на шпильке: канва GG, кожаный мысок и пряжка Horsebit. {ASK_LUXE}",
        None,
        None,
        NO_SIZE,
        1,
        supplier("gucci-slingbek-horsebit", "luxe"),
    ),
    (
        21,
        5,
        "Gucci — кеды Screener",
        "gucci-kedy-screener",
        f"Кеды Screener с эффектом винтажа, канвой GG и полосой Web. {ASK_LUXE}",
        None,
        None,
        NO_SIZE,
        1,
        supplier("gucci-kedy-screener", "luxe"),
    ),
    (
        22,
        5,
        "Gucci — сумка GG из денима",
        "gucci-sumka-gg-denim",
        f"Сумка на плечо из денима с жаккардом GG и кожаными ручками. {ASK_LUXE}",
        None,
        None,
        NO_SIZE,
        1,
        supplier("gucci-sumka-gg-denim", "luxe", 2),
    ),
    # --- Для дома (Stanley) ---
    (
        23,
        6,
        "Stanley — шейкер-термос 591 мл",
        "stanley-sheyker-termos-591",
        f"Шейкер-термос на 591 мл с откидной ручкой — для протеина, смузи и воды. {ON_ORDER}",
        3_600,
        None,
        NO_SIZE,
        10,
        supplier("stanley-sheyker-termos-591", "804739"),
    ),
    (
        24,
        6,
        "Stanley — термобутылка 473 мл",
        "stanley-termobutylka-473",
        "Термобутылка на 473 мл с цветочным принтом и откидной крышкой. Голубая или розовая — "
        f"укажите цвет в комментарии к заказу. {ON_ORDER}",
        4_500,
        None,
        NO_SIZE,
        10,
        supplier("stanley-termobutylka-473", "804690"),
    ),
    (
        25,
        6,
        "Stanley × LoveShackFancy — термосумка",
        "stanley-termosumka-loveshackfancy",
        "Термосумка 24 × 20 × 25 см с принтом из бантов, ручками и ремнём через плечо. Розовая "
        f"или голубая — укажите цвет в комментарии к заказу. {ON_ORDER}",
        14_700,
        None,
        NO_SIZE,
        10,
        supplier("stanley-termosumka-loveshackfancy", "804811"),
    ),
    (
        26,
        6,
        "Stanley — трубочки многоразовые, 4 шт.",
        "stanley-trubochki-mnogorazovye",
        f"Сменные трубочки для стакана Stanley Quencher, 4 шт. разных цветов. {ON_ORDER}",
        1_700,
        None,
        NO_SIZE,
        10,
        supplier("stanley-trubochki-mnogorazovye", "804815"),
    ),
    # --- В наличии: по одной вещи, отправляем сразу ---
    (
        27,
        7,
        "Puma Velophasis",
        "puma-velophasis-9-5-us",
        f"Кроссовки Puma Velophasis, размер 9,5 US (42,5–43 EU). {IN_STOCK}",
        11_000,
        None,
        ("9,5 US",),
        1,
        supplier("puma-velophasis-9-5-us", "nalichie", 4),
    ),
    (
        28,
        7,
        "Adidas Nora",
        "adidas-nora-8-us",
        f"Кеды Adidas Nora, размер 8 US (38,5–39 EU). {IN_STOCK}",
        11_000,
        None,
        ("8 US",),
        1,
        supplier("adidas-nora-8-us", "nalichie", 2),
    ),
    (
        29,
        7,
        "Ralph Lauren — поло детское",
        "ralph-lauren-polo-detskoe",
        "Классическое поло из пике на 10–12 лет. Вместе с белыми брюками — готовый наряд. "
        f"{IN_STOCK}",
        3_000,
        None,
        ("10–12 лет",),
        1,
        supplier("ralph-lauren-polo-detskoe", "nalichie", 2),
    ),
    (
        30,
        7,
        "Ralph Lauren — брюки детские",
        "ralph-lauren-bryuki-detskie",
        f"Белые брюки-чинос на 12 лет. Вместе с красным поло — готовый наряд. {IN_STOCK}",
        3_000,
        None,
        ("12 лет",),
        1,
        supplier("ralph-lauren-bryuki-detskie", "nalichie", 2),
    ),
    (
        31,
        7,
        "Calvin Klein — худи вязаное",
        "calvin-klein-hudi-xs",
        f"Вязаное худи Calvin Klein Jeans, размер XS. Очень мягкое и приятное. {IN_STOCK}",
        8_000,
        None,
        ("XS",),
        1,
        supplier("calvin-klein-hudi-xs", "nalichie", 6),
    ),
]

START = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def kopecks(rubles: int | None) -> int | None:
    return rubles * 100 if rubles is not None else None


def build():
    previous = {entry["slug"]: entry for entry in json.loads(MANIFEST.read_text("utf-8"))}
    objects = []
    for position, (pk, name, slug) in enumerate(CATEGORIES):
        objects.append(
            {
                "model": "store.category",
                "pk": pk,
                "fields": {
                    "name": name,
                    "slug": slug,
                    "parent": None,
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
        images,
    ) in enumerate(PRODUCTS):
        # Новые товары выше: первый в списке — самый свежий.
        created = iso(START + timedelta(hours=len(PRODUCTS) - index))
        objects.append(
            {
                "model": "store.product",
                "pk": pk,
                "fields": {
                    "name": name,
                    "slug": slug,
                    "description": description,
                    "category": category,
                    "price_kopecks": kopecks(price),
                    "compare_at_kopecks": kopecks(old),
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
                        "sku": f"DD-{pk}-{size}".replace(" ", "") if size else f"DD-{pk}",
                        "stock": stock,
                        "position": position,
                        "created_at": created,
                        "updated_at": created,
                        "deleted_at": None,
                    },
                }
            )
        if images is KEEP:
            manifest.append(previous[slug])
        else:
            manifest.append({"slug": slug, "images": images})

    (ROOT / "fixtures/catalog.json").write_text(
        json.dumps(objects, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
