"""Визуальное превью витрины для GitHub Pages: все «комнаты» сайта статичными страницами.

Страницы рендерятся настоящими шаблонами и view витрины (Django test Client) на демо-каталоге
и демо-заказах, поэтому любая правка вёрстки, стилей или токенов сразу видна в превью.
Два дерева страниц: гость — `<base>/…`, вошедший покупатель — `<base>/me/…`; отдельные
состояния (ошибки форм, проблемная корзина, баннер) — `<base>/rooms/…`, оглавление —
`<base>/rooms/`. Отправка форм и корзину имитирует static/preview/preview.js (только здесь,
на боевом сайте его нет).

Запуск (нужен Postgres из DB_*):
    PREVIEW_BASE=/ThreadsAndTrends-Django-Emporium python deploy/preview/build.py _site
"""

import json
import os
import re
import shutil
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deploy.preview.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import AnonymousUser  # noqa: E402
from django.core.cache import cache  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.template.loader import render_to_string  # noqa: E402
from django.test import Client, RequestFactory  # noqa: E402
from django.urls import set_script_prefix  # noqa: E402
from django.utils import timezone  # noqa: E402

from content.models import Article  # noqa: E402
from orders.models import ChangedBy, DeliveryMethod, Order, OrderStatus, PaymentMethod  # noqa: E402
from orders.services import checkout as checkout_service  # noqa: E402
from orders.services import status as status_service  # noqa: E402
from payments import providers  # noqa: E402
from payments import services as payments  # noqa: E402
from payments.tests.fake import FakeProvider  # noqa: E402
from store.models import CartItem, Category, Product, ProductVariant  # noqa: E402
from store.services import cart as cart_service  # noqa: E402

User = get_user_model()
S = OrderStatus

BASE = settings.PREVIEW_BASE  # "/Repo" или ""
ME = f"{BASE}/me"
PASSWORD = "Preview-Passw0rd!"
CUSTOMER_EMAIL = "anna@example.ru"
IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)

HTMX_TAG = re.compile(r'\s*<script src="[^"]*/htmx-[^"]*"[^>]*></script>')


class Site:
    """Рендер страниц в папку сайта с учётом префикса дерева (гость / покупатель)."""

    def __init__(self, out: Path):
        self.out = out
        self.pages: set[str] = set()  # адреса отрендеренных страниц (для переключателя)
        self._prefix: str | None = None

    def _use(self, prefix: str) -> None:
        # Готовые сетки товаров в кэше содержат ссылки с префиксом дерева: при смене дерева
        # кэш сбрасывается (заодно и счётчики лимитов попыток).
        if prefix != self._prefix:
            cache.clear()
            self._prefix = prefix

    def request(self, client: Client, prefix: str, path: str, *, data=None, **extra):
        self._use(prefix)
        # Тестовый клиент, в отличие от WSGIHandler, не ставит префикс для reverse() сам.
        set_script_prefix(prefix + "/")
        if data is None:
            return client.get(path, SCRIPT_NAME=prefix, **extra)
        return client.post(path, data, SCRIPT_NAME=prefix, **extra)

    def follow(self, client: Client, prefix: str, response):
        """Редирект внутри сайта: адрес в Location уже с префиксом — убираем его."""
        while response.status_code in (301, 302):
            location = urlsplit(response["Location"])
            path = unquote(location.path)
            assert path.startswith(prefix + "/"), response["Location"]
            target = path[len(prefix) :] + (f"?{location.query}" if location.query else "")
            response = self.request(client, prefix, target)
        return response

    def save(self, client, prefix, path, target=None, *, tree, room="", status=200, **kwargs):
        """Отрендерить `path` и сохранить как `<target>/index.html` (target — адрес на Pages
        без BASE; по умолчанию = префикс дерева + path без query)."""
        response = self.follow(client, prefix, self.request(client, prefix, path, **kwargs))
        assert response.status_code == status, (path, response.status_code)
        if target is None:
            target = prefix[len(BASE) :] + path.split("?")[0]
        html = self.decorate(response.content.decode(), tree=tree, room=room)
        if target.endswith(".html"):
            file = self.out / target.lstrip("/")
        else:
            file = self.out / target.strip("/") / "index.html"
            self.pages.add(BASE + "/" + target.strip("/") + ("/" if target.strip("/") else ""))
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(html, encoding="utf-8")
        return response

    @staticmethod
    def decorate(html: str, *, tree: str, room: str = "") -> str:
        """Подключить превью: без htmx (формы перехватывает preview.js), тема до отрисовки,
        закрыто от поисковиков."""
        html = HTMX_TAG.sub("", html)
        attrs = f' data-preview-base="{BASE}" data-preview-tree="{tree}"'
        if room:
            attrs += f' data-preview-room="{room}"'
        html = html.replace('<html lang="ru"', '<html lang="ru"' + attrs, 1)
        head = (
            '<meta name="robots" content="noindex, nofollow">\n'
            f'  <script src="{BASE}/static/preview/theme.js"></script>\n'
            f'  <link rel="stylesheet" href="{BASE}/static/preview/preview.css">\n'
        )
        html = html.replace("</head>", head + "</head>", 1)
        body = f'<script src="{BASE}/static/preview/preview.js" defer></script>\n'
        return html.replace("</body>", body + "</body>", 1)


# --- Данные ---


def in_stock_variants() -> list[ProductVariant]:
    live = Product.objects.live().values_list("pk", flat=True)
    return list(
        ProductVariant.objects.filter(product__in=live, deleted_at=None, stock__gt=0)
        .select_related("product")
        .order_by("product__category_id", "product_id", "position", "pk")
    )


BACKDATE: dict[int, int] = {}


def make_customer(email: str, first_name: str) -> User:
    return User.objects.create_user(email=email, password=PASSWORD, first_name=first_name)


def place_order(user, variants, *, delivery, payment, days_ago=0) -> Order:
    for variant, quantity in variants:
        cart_service.add(user, variant.pk, quantity)
    order, _ = checkout_service.checkout(
        user,
        checkout_service.CheckoutInput(
            delivery_method=delivery,
            payment_method=payment,
            recipient_name="Анна Смирнова",
            recipient_phone="+7 900 555-12-34",
            delivery_address=(
                "Москва, ул. Лесная, 12, кв. 45" if delivery == DeliveryMethod.COURIER else ""
            ),
            comment="Позвонить за час" if days_ago % 2 else "",
        ),
        os.urandom(12).hex(),
    )
    if days_ago:
        # Дата сдвигается после всех переходов: иначе оплата «опоздала» бы (срок — 30 мин).
        BACKDATE[order.pk] = days_ago
    return order


def pay(order: Order, fake: FakeProvider) -> Order:
    payment = payments.start_payment(order, return_url=f"http://testserver/orders/{order.number}/")
    fake.pay(payment.provider_payment_id)
    payments.sync_order_payments(order)
    order.refresh_from_db()
    return order


def move(order: Order, *statuses: str) -> Order:
    for target in statuses:
        order = status_service.transition(order, target, by=ChangedBy.ADMIN)
    return order


def demo_orders(user, variants, fake) -> list[Order]:
    """Заказы во всех статусах: от старых к новым (в «Моих заказах» новые сверху)."""
    v = variants
    C, P = DeliveryMethod.COURIER, DeliveryMethod.PICKUP
    ON, OFF = PaymentMethod.ONLINE, PaymentMethod.ON_DELIVERY
    orders = []
    orders.append(
        move(
            place_order(user, [(v[0], 1), (v[5], 2)], delivery=C, payment=OFF, days_ago=40),
            S.ASSEMBLED,
            S.SHIPPED,
            S.DELIVERED,
        )
    )
    paid_cancelled = pay(place_order(user, [(v[8], 1)], delivery=C, payment=ON, days_ago=21), fake)
    orders.append(status_service.cancel(paid_cancelled, by=ChangedBy.CUSTOMER, actor=user))
    orders.append(
        status_service.cancel(
            place_order(user, [(v[3], 1)], delivery=P, payment=OFF, days_ago=14),
            by=ChangedBy.CUSTOMER,
            actor=user,
        )
    )
    orders.append(
        move(
            place_order(user, [(v[10], 1)], delivery=P, payment=OFF, days_ago=6),
            S.ASSEMBLED,
            S.READY_FOR_PICKUP,
        )
    )
    orders.append(
        move(
            pay(
                place_order(user, [(v[12], 1), (v[2], 1)], delivery=C, payment=ON, days_ago=4), fake
            ),
            S.ASSEMBLED,
            S.SHIPPED,
        )
    )
    orders.append(
        move(place_order(user, [(v[6], 3)], delivery=C, payment=OFF, days_ago=3), S.ASSEMBLED)
    )
    orders.append(pay(place_order(user, [(v[14], 1)], delivery=C, payment=ON, days_ago=2), fake))
    orders.append(place_order(user, [(v[1], 1), (v[9], 1)], delivery=C, payment=OFF, days_ago=1))
    orders.append(place_order(user, [(v[4], 2)], delivery=C, payment=ON))
    now = timezone.now()
    for pk, days in BACKDATE.items():
        Order.objects.filter(pk=pk).update(created_at=now - timedelta(days=days))
    return [Order.objects.get(pk=order.pk) for order in orders]


# --- Сборка ---


def catalog_paths() -> list[str]:
    paths = ["/", "/products/", "/contacts/"]
    paths += [f"/category/{c.slug}/" for c in Category.objects.filter(is_active=True)]
    paths += [f"/product/{p.slug}/" for p in Product.objects.live()]
    paths += [f"/articles/{a.slug}/" for a in Article.objects.filter(is_published=True)]
    paths += ["/legal/offer/", "/legal/privacy/", "/legal/delivery/"]
    return paths


def search_query() -> str:
    first = Product.objects.live().order_by("pk").first()
    return first.name.split()[0].lower()


def build(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    media = Path(settings.MEDIA_ROOT)
    if media.exists():
        shutil.rmtree(media)

    call_command("migrate", verbosity=0)
    call_command("seed_demo", verbosity=0)

    fake = FakeProvider()
    providers.get_provider = lambda: fake  # платежи и возвраты — в памяти, без сети

    variants = in_stock_variants()
    customer = make_customer(CUSTOMER_EMAIL, "Анна")
    orders = demo_orders(customer, variants, fake)

    site = Site(out)
    guest, me = Client(), Client()
    me.force_login(customer)
    query = search_query()

    # Гость
    for path in catalog_paths():
        site.save(guest, BASE, path, tree="guest")
    site.save(guest, BASE, f"/search/?q={query}", tree="guest")
    site.save(guest, BASE, "/cart/", tree="guest")
    for path in ("/login/", "/register/", "/password-reset/", "/profile/"):
        site.save(guest, BASE, path, tree="guest")
    site.save(guest, BASE, f"/password-reset/confirm/?email={CUSTOMER_EMAIL}", tree="guest")
    # Оформление и заказы гостю недоступны — там страница входа, как на сайте.
    site.save(guest, BASE, "/checkout/", tree="guest")
    site.save(guest, BASE, "/orders/", tree="guest")

    # Покупатель
    for path in catalog_paths():
        site.save(me, ME, path, tree="me")
    site.save(me, ME, f"/search/?q={query}", tree="me")
    site.save(me, ME, "/cart/", tree="me")
    for path in ("/profile/", "/profile/password/", "/profile/delete/", "/orders/"):
        site.save(me, ME, path, tree="me")
    for order in orders:
        site.save(me, ME, f"/orders/{order.number}/", tree="me")
    for variant, quantity in ((variants[0], 1), (variants[7], 2)):
        cart_service.add(customer, variant.pk, quantity)
    site.save(me, ME, "/checkout/", tree="me")
    rooms = render_rooms_states(site, guest, me, customer, variants, query, fake)
    site.save(guest, BASE, "/no-such-page/", "/404.html", tree="guest", status=404)

    # Данные имитации: корзина со всеми товарами (строки берутся из настоящего шаблона).
    sim_cart(site, variants)
    data = {
        "base": BASE,
        "pages": sorted(site.pages),
        "freeFrom": settings.DELIVERY_FREE_FROM_KOPECKS,
        "courier": settings.DELIVERY_COURIER_KOPECKS,
        "maxQuantity": settings.CART_MAX_QUANTITY,
        "variants": {
            str(v.pk): {
                "name": v.product.name,
                "size": v.size,
                "price": v.product.price_kopecks,
                "max": min(v.stock, settings.CART_MAX_QUANTITY),
            }
            for v in variants
        },
    }
    (out / "static/preview").mkdir(parents=True)
    write_rooms(out, orders, rooms, query)

    shutil.copytree(ROOT / "web/static", out / "static", dirs_exist_ok=True)
    shutil.copytree(ROOT / "deploy/preview/assets", out / "static/preview", dirs_exist_ok=True)
    (out / "static/preview/data.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    if media.exists():
        shutil.copytree(media, out / "media")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Превью: {len(site.pages)} страниц → {out}")


def render_rooms_states(site, guest, me, customer, variants, query, fake) -> dict:
    """Отдельные состояния страниц, которых нет при обычной навигации."""
    rooms = {}

    def room(key, title, client, prefix, path, *, tree, **kwargs):
        target = f"/rooms/{key}/"
        site.save(client, prefix, path, target, tree=tree, room=key, **kwargs)
        rooms[key] = (title, BASE + target)

    room("search-empty", "Поиск без результатов", guest, BASE, "/search/?q=пылесос", tree="guest")
    room(
        "app-banner",
        "Баннер «Скачать приложение» (iPhone)",
        guest,
        BASE,
        "/",
        tree="guest",
        HTTP_USER_AGENT=IPHONE_UA,
    )
    room(
        "login-error",
        "Вход: неверный пароль",
        guest,
        BASE,
        "/login/",
        tree="guest",
        data={"email": CUSTOMER_EMAIL, "password": "wrong-password"},
    )
    room(
        "register-errors",
        "Регистрация: ошибки в полях",
        guest,
        BASE,
        "/register/",
        tree="guest",
        data={"email": "not-an-email", "password": "123", "first_name": ""},
    )
    room(
        "reset-code-error",
        "Сброс пароля: неверный код",
        guest,
        BASE,
        "/password-reset/confirm/",
        tree="guest",
        data={"email": CUSTOMER_EMAIL, "code": "000000", "new_password": "New-Passw0rd!"},
    )
    room(
        "checkout-errors",
        "Оформление: не заполнены поля",
        me,
        ME,
        "/checkout/",
        tree="me",
        data={
            "delivery_method": "courier",
            "payment_method": "on_delivery",
            "recipient_name": "",
            "recipient_phone": "123",
            "delivery_address": "",
            "expected_total": "0",
            "idempotency_key": "preview-errors-0001",
        },
    )

    # «Заказ оформлен»: настоящее оформление и страница заказа с сообщением.
    response = site.request(me, ME, "/checkout/")
    key = re.search(r'name="idempotency_key" value="([^"]+)"', response.content.decode())[1]
    total = re.search(r'name="expected_total" value="(\d+)"', response.content.decode())[1]
    form = {
        "delivery_method": "courier",
        "payment_method": "on_delivery",
        "recipient_name": "Анна Смирнова",
        "recipient_phone": "+79005551234",
        "delivery_address": "Москва, ул. Лесная, 12, кв. 45",
        "comment": "",
        "expected_total": total,
        "idempotency_key": key,
    }
    response = site.request(me, ME, "/checkout/", data=form)
    site.save(
        me,
        ME,
        unquote(urlsplit(response["Location"]).path)[len(ME) :],
        "/me/orders/placed/",
        tree="me",
        room="placed",
    )
    rooms["placed"] = ("Заказ оформлен (оплата при получении)", f"{ME}/orders/placed/")

    online = place_order(
        customer, [(variants[3], 1)], delivery=DeliveryMethod.COURIER, payment=PaymentMethod.ONLINE
    )
    payments.start_payment(online, return_url=f"http://testserver/orders/{online.number}/")
    site.save(
        me,
        ME,
        f"/orders/{online.number}/?paid=1",
        "/me/orders/placed-online/",
        tree="me",
        room="placed-online",
    )
    rooms["placed-online"] = (
        "Вернулся со страницы оплаты (ожидает оплаты)",
        f"{ME}/orders/placed-online/",
    )

    # Корзина с проблемами: цена изменилась, нет в наличии, больше остатка, товар скрыт.
    problem = make_customer("problem@example.ru", "Пётр")
    picks = [variants[0], variants[4], variants[9], variants[13]]
    for variant in picks:
        cart_service.add(problem, variant.pk, 1)
    items = CartItem.objects.filter(cart__owner=problem)
    items.filter(variant=picks[0]).update(
        seen_price_kopecks=picks[0].product.price_kopecks - 300_00
    )
    ProductVariant.objects.filter(pk=picks[1].pk).update(stock=0)
    ProductVariant.objects.filter(pk=picks[2].pk).update(stock=1)
    items.filter(variant=picks[2]).update(quantity=3)
    Product.objects.filter(pk=picks[3].product_id).update(is_active=False)
    client = Client()
    client.force_login(problem)
    room(
        "cart-problems",
        "Корзина: цена изменилась, нет в наличии, скрытый товар",
        client,
        ME,
        "/cart/",
        tree="me",
    )
    Product.objects.filter(pk=picks[3].product_id).update(is_active=True)
    ProductVariant.objects.filter(pk=picks[1].pk).update(stock=picks[1].stock)
    ProductVariant.objects.filter(pk=picks[2].pk).update(stock=picks[2].stock)
    return rooms


def sim_cart(site: Site, variants) -> None:
    """Корзины со всеми товарами в наличии (гость и покупатель) и фрагмент «Добавлено»:
    preview.js берёт из них разметку строк и пересчитывает количество и суммы."""
    guest = Client()
    for variant in variants:
        site.request(guest, BASE, "/cart/add/", data={"variant": variant.pk, "quantity": 1})
    site.save(guest, BASE, "/cart/", "/_sim/cart-guest/", tree="guest", room="sim")
    added = site.request(
        guest, BASE, "/cart/add/", data={"variant": variants[0].pk}, HTTP_HX_REQUEST="true"
    )
    (site.out / "_sim").mkdir(exist_ok=True)
    (site.out / "_sim/added-guest.html").write_bytes(added.content)

    buyer = make_customer("sim@example.ru", "Сим")
    for variant in variants:
        cart_service.add(buyer, variant.pk, 1)
    client = Client()
    client.force_login(buyer)
    site.save(client, ME, "/cart/", "/_sim/cart-me/", tree="me", room="sim")
    added = site.request(
        client, ME, "/cart/add/", data={"variant": variants[0].pk}, HTTP_HX_REQUEST="true"
    )
    (site.out / "_sim/added-me.html").write_bytes(added.content)
    site.pages -= {f"{BASE}/_sim/cart-guest/", f"{BASE}/_sim/cart-me/"}


def write_rooms(out: Path, orders: list[Order], rooms: dict, query: str) -> None:
    """Оглавление «Все комнаты» — в стиле витрины (наследует web/base.html)."""
    g, m = BASE, ME
    root_category = Category.objects.filter(is_active=True, parent=None).first()
    sections = [
        (
            "Каталог",
            [
                ("Главная", f"{g}/"),
                ("Все товары", f"{g}/products/"),
                (f"Поиск «{query}»", f"{g}/search/"),
                rooms.pop("search-empty"),
                ("Категория", f"{g}/category/{root_category.slug}/"),
                ("Товар со скидкой", product_link(compare=True)),
                ("Товар без размеров", product_link(single=True)),
                ("Нет в наличии", product_link(sold_out=True)),
                rooms.pop("app-banner"),
            ],
        ),
        (
            "Корзина и оформление",
            [
                ("Корзина гостя (имитация)", f"{g}/cart/"),
                ("Корзина покупателя (имитация)", f"{m}/cart/"),
                rooms.pop("cart-problems"),
                ("Оформление заказа", f"{m}/checkout/"),
                rooms.pop("checkout-errors"),
                rooms.pop("placed"),
                rooms.pop("placed-online"),
            ],
        ),
        (
            "Мои заказы",
            [("Список заказов", f"{m}/orders/")]
            + [
                (
                    f"{order.number} — {S(order.status).label}"
                    + (
                        " (возврат)"
                        if order.status == S.CANCELLED
                        and order.payment_method == PaymentMethod.ONLINE
                        else ""
                    ),
                    f"{m}/orders/{order.number}/",
                )
                for order in orders
            ],
        ),
        (
            "Профиль и вход",
            [
                ("Профиль гостя", f"{g}/profile/"),
                ("Профиль покупателя", f"{m}/profile/"),
                ("Смена пароля", f"{m}/profile/password/"),
                ("Удаление аккаунта", f"{m}/profile/delete/"),
                ("Вход", f"{g}/login/"),
                rooms.pop("login-error"),
                ("Регистрация", f"{g}/register/"),
                rooms.pop("register-errors"),
                ("Сброс пароля: email", f"{g}/password-reset/"),
                ("Сброс пароля: код", f"{g}/password-reset/confirm/"),
                rooms.pop("reset-code-error"),
            ],
        ),
        (
            "Контакты и страницы",
            [
                ("Контакты", f"{g}/contacts/"),
                (
                    "Статья",
                    f"{g}/articles/{Article.objects.filter(is_published=True).first().slug}/",
                ),
                ("Оферта", f"{g}/legal/offer/"),
                ("Политика ПДн", f"{g}/legal/privacy/"),
                ("Доставка и возврат", f"{g}/legal/delivery/"),
                ("Страница 404", f"{g}/404.html"),
            ],
        ),
    ]
    request = RequestFactory().get("/rooms/")
    request.user = AnonymousUser()
    set_script_prefix(BASE + "/")
    html = render_to_string(
        "preview/rooms.html", {"sections": sections, "noindex": True}, request=request
    )
    set_script_prefix("/")
    file = out / "rooms/index.html"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(Site.decorate(html, tree="guest", room="rooms"), encoding="utf-8")


def product_link(*, compare=False, single=False, sold_out=False) -> str:
    products = Product.objects.live().with_stock().order_by("pk")
    for product in products:
        sizes = [v.size for v in product.variants.all()]
        if compare and not product.compare_at_kopecks:
            continue
        if single and sizes != [""]:
            continue
        if sold_out and product.total_stock:
            continue
        if not sold_out and not product.total_stock:
            continue
        return f"{BASE}/product/{product.slug}/"
    return f"{BASE}/"


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve())
