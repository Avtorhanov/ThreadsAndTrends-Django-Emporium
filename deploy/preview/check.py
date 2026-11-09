"""Проверка собранного превью в браузере (Playwright): каждая страница открывается без ошибок
в консоли и без битых ресурсов; имитация работает от начала до конца (товар → корзина → вход →
оформление → заказ виден в панели; новый товар из панели открывается в магазине); скриншоты
ключевых комнат на телефоне и десктопе в обеих темах. Панель администратора (`/panel/`) — каждый
экран открывается с данными, без сообщений об ошибке; скриншоты — panel-*.

    python deploy/preview/check.py _site shots
Сайт раздаётся локально по тому же пути, что на Pages (PREVIEW_BASE).
"""

import base64
import functools
import http.server
import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

BASE = os.environ.get("PREVIEW_BASE", "").rstrip("/")
IPHONE = {
    "viewport": {"width": 390, "height": 844},
    "device_scale_factor": 3,
    "is_mobile": True,
    "has_touch": True,
}
DESKTOP = {"viewport": {"width": 1280, "height": 860}}
SHOTS = [  # (имя, адрес без BASE)
    ("home", "/"),
    ("product", None),  # первый товар из data.json
    ("cart-empty", "/cart/"),
    ("contacts", "/contacts/"),
    ("profile-guest", "/profile/"),
    ("profile-me", "/me/profile/"),
    ("profile-data-me", "/me/profile/data/"),
    ("profile-look", "/profile/look/"),
    ("orders-me", "/me/orders/"),
    ("rooms", "/rooms/"),
]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Как GitHub Pages: несуществующий адрес — 404.html сайта с кодом 404."""

    site: Path

    def log_message(self, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        page = self.site / "404.html"
        if code != 404 or not page.exists():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def serve(site: Path) -> tuple[str, http.server.ThreadingHTTPServer]:
    """Раздать папку сайта под путём BASE (как project site на github.io)."""
    holder = Path(tempfile.mkdtemp())
    target = holder / BASE.strip("/") if BASE else holder
    if BASE:
        target.symlink_to(site.resolve(), target_is_directory=True)
    else:
        holder = site.resolve()
    QuietHandler.site = site.resolve()
    handler = functools.partial(QuietHandler, directory=str(holder))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", server


def main(site: Path, shots: Path) -> None:
    shots.mkdir(parents=True, exist_ok=True)
    data = json.loads((site / "static/preview/data.json").read_text(encoding="utf-8"))
    origin, server = serve(site)
    problems: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        def page_for(device, theme=None, *, pages_404=False):
            """pages_404 — адреса новых товаров и заказов: Pages отвечает 404.html (это норма)."""
            context = browser.new_context(**device, locale="ru-RU")
            if theme:
                context.add_cookies([{"name": "theme", "value": theme, "url": origin}])
            page = context.new_page()

            def on_console(msg):
                if msg.type == "error" and not (pages_404 and "404" in msg.text):
                    problems.append(f"{page.url}: {msg.text}")

            def on_response(response):
                expected = pages_404 and response.request.is_navigation_request()
                if response.status >= 400 and not (expected and response.status == 404):
                    problems.append(f"{response.status} {response.url}")

            page.on("dialog", lambda dialog: dialog.accept())
            page.on("console", on_console)
            page.on("pageerror", lambda exc: problems.append(f"{page.url}: {exc}"))
            page.on("response", on_response)
            return page

        # 1. Все страницы открываются чисто.
        page = page_for(DESKTOP)
        for path in data["pages"] + [f"{BASE}/rooms/"]:
            page.goto(origin + path, wait_until="load")
        print(f"Страниц проверено: {len(data['pages']) + 1}")

        # 1а. Прокрутка: вниз — нижнее меню уезжает и шапка сворачивается, вверх посреди ленты —
        # оба меню возвращаются (шапка — с категориями); у начала страницы шапка без стекла.
        page = page_for(IPHONE)
        page.goto(origin + BASE + "/", wait_until="load")
        page.mouse.wheel(0, 900)
        page.wait_for_function("document.documentElement.dataset.bars === 'hidden'")
        assert page.locator("[data-header].is-compact").count() == 1
        page.mouse.wheel(0, -200)
        page.wait_for_function("!document.documentElement.dataset.bars")
        assert page.locator("[data-header].is-revealed:not(.is-compact)").count() == 1
        page.screenshot(path=shots / "scroll-up-bars-iphone.png")
        print("Меню при прокрутке: прячутся вниз, возвращаются вверх: ок")

        # 1б. Масштаб интерфейса (профиль → «Оформление»): весь интерфейс пропорционально,
        # страница не шире экрана ни на 80 %, ни на 150 %.
        for scale in ("80", "150"):
            page = page_for(IPHONE)
            page.context.add_cookies([{"name": "text_size", "value": scale, "url": origin}])
            for path in ("/", "/cart/", "/profile/look/"):
                page.goto(origin + BASE + path, wait_until="load")
                assert page.get_attribute("html", "data-text") == scale, (
                    f"масштаб {scale} не применён"
                )
                wide = page.evaluate(
                    "document.documentElement.scrollWidth - document.documentElement.clientWidth"
                )
                assert wide <= 1, f"{path} при {scale} %: шире экрана на {wide} px"
            page.goto(origin + BASE + "/", wait_until="load")
            page.screenshot(path=shots / f"scale-{scale}-iphone.png")
        print("Масштаб 80 % и 150 %: вёрстка в ширину экрана: ок")

        # 2. Покупатель: товар → корзина (+1) → вход → оформление → страница заказа.
        page = page_for(IPHONE, pages_404=True)
        check = data["check"]
        variant, name = check["variant"], check["name"]
        page.goto(origin + BASE + check["path"], wait_until="load")
        page.click(f'label.sz:has(input[value="{variant}"])')
        page.click("[data-cta]")
        page.wait_for_selector("[data-added]")
        assert page.text_content("#cart-badge-tab").strip() == "1"
        page.goto(origin + f"{BASE}/cart/", wait_until="load")
        page.wait_for_selector(".lines .line")
        page.click('form[data-op="inc"] button')
        page.wait_for_selector(".stepper__value:text-is('2')")
        page.screenshot(path=shots / "sim-cart-iphone.png")
        page.goto(origin + f"{BASE}/login/?next=/checkout/", wait_until="load")
        page.fill('main input[name="email"]', data["customer"]["email"])
        page.fill('main input[name="password"]', data["customer"]["password"])
        page.click('main form[method="post"] button[type="submit"]')
        page.wait_for_url(f"**{BASE}/me/checkout/")
        page.wait_for_selector(f".mini li:has-text('{name}')")
        # Выключенные в панели способы оплаты покупатель не видит (в HTML демо есть все).
        visible = page.locator('.choice:visible input[name="payment_method"]')
        assert visible.count() == 1 and visible.first.get_attribute("value") == "agreement"
        page.screenshot(path=shots / "sim-checkout-iphone.png", full_page=True)
        page.click("[data-checkout] button[type=submit]")
        page.wait_for_url(f"**{BASE}/me/orders/DD-*/")
        page.wait_for_selector(".page .h1:has-text('Заказ')")
        number = page.text_content(".page .h1 .nowrap").strip()
        assert page.evaluate("window.DidiSim.cartCount()") == 0
        # Демо как на запуске: заказ ждёт согласования, кнопка WhatsApp с текстом заказа.
        page.wait_for_selector(".status:text-is('Ждёт согласования')")
        href = page.get_attribute(".agree__go", "href")
        assert href.startswith("https://wa.me/") and number in unquote(href), href
        page.screenshot(path=shots / "sim-order-iphone.png", full_page=True)
        print(f"Имитация: корзина и оформление — заказ {number}, кнопка WhatsApp с текстом заказа")

        # 2а. Гость: корзина → оформление без аккаунта → ссылка → вход привязывает заказ.
        page = page_for(IPHONE, pages_404=True)
        page.goto(origin + BASE + check["path"], wait_until="load")
        page.click(f'label.sz:has(input[value="{variant}"])')
        page.click("[data-cta]")
        page.wait_for_selector("[data-added]")
        page.goto(origin + f"{BASE}/cart/", wait_until="load")
        page.click(".cta--link")
        page.wait_for_url(f"**{BASE}/checkout/")
        page.fill('[name="recipient_name"]', "Гость Проверки")
        page.fill('[name="recipient_phone"]', "+7 900 555-44-33")
        page.fill('[name="delivery_address"]', "Москва, ул. Ленина, 1, кв. 1")
        page.check('[name="consent"]')
        page.screenshot(path=shots / "sim-guest-checkout-iphone.png", full_page=True)
        page.click("[data-checkout] button[type=submit]")
        page.wait_for_url(f"**{BASE}/order/g/*/")
        page.wait_for_selector(".guest-link")
        guest_number = page.text_content(".page .h1 .nowrap").strip()
        page.screenshot(path=shots / "sim-guest-order-iphone.png", full_page=True)
        page.goto(origin + f"{BASE}/login/", wait_until="load")
        page.fill('main input[name="email"]', data["customer"]["email"])
        page.fill('main input[name="password"]', data["customer"]["password"])
        page.click('main form[method="post"] button[type="submit"]')
        page.wait_for_url(f"**{BASE}/me/**")
        page.goto(origin + f"{BASE}/me/orders/{guest_number}/", wait_until="load")
        page.wait_for_selector(f".page .h1:has-text('{guest_number}')")
        print(f"Имитация: заказ гостя {guest_number} оформлен и привязан при входе")

        # 3. Тот же заказ — в панели; товар, созданный в панели, — в магазине.
        page.evaluate("localStorage.setItem('didi-preview-admin', '1')")
        page.goto(origin + f"{BASE}/panel/orders/", wait_until="load")
        page.wait_for_selector(f"text={number}")
        created = page.evaluate(
            """async () => {
              const result = await window.DidiSim.api("POST", "/api/v1/admin/catalog/products/", {
                name: "Демо-товар проверки", category: window.DidiSim.categories()[0].id,
                price_kopecks: 123400, variants: [{ size: "M" }],
              });
              const variant = result.body.variants[0].id;
              const url = `/api/v1/admin/catalog/variants/${variant}/`;
              await window.DidiSim.api("PATCH", url, { stock: 5 });
              return result.body;
            }"""
        )
        page.goto(origin + f"{BASE}/product/{created['slug']}/", wait_until="load")
        page.wait_for_selector(".pd__title:has-text('Демо-товар проверки')")
        page.goto(origin + f"{BASE}/panel/catalog/products/{created['id']}/", wait_until="load")
        page.wait_for_function(
            "[...document.querySelectorAll('main input')]"
            ".some((input) => input.value === 'Демо-товар проверки')"
        )
        print("Имитация: заказ виден в панели, новый товар открывается в магазине и в панели")

        page.evaluate("localStorage.removeItem('didi-preview-admin')")
        # 3б. B13 (после панели — заказ здесь отменяется): фото на весь экран и «Поделиться»;
        # смена email кодом; точка «есть новости».
        page.goto(origin + BASE + check["path"], wait_until="load")
        page.wait_for_selector(".pd__share")
        page.click("[data-zoom]")
        page.wait_for_selector(".pswp--open .pswp__img", timeout=10_000)
        page.wait_for_timeout(700)  # анимация открытия
        page.click(".pswp__button--close")
        page.wait_for_selector(".pswp", state="detached", timeout=10_000)
        page.goto(origin + f"{BASE}/me/profile/data/", wait_until="load")
        assert page.locator("text=логин аккаунта").count() == 0, "осталась подпись про логин"
        new_email = "new-" + data["customer"]["email"]
        page.fill('#email [name="new_email"]', new_email)
        page.fill('#email [name="password"]', data["customer"]["password"])
        page.click('#email button[type="submit"]')
        page.wait_for_selector('#email [name="code"]')
        page.fill('#email [name="code"]', "123456")
        page.click('#email form button[type="submit"]')
        page.wait_for_selector(f"#email .readonly:has-text('{new_email}')")
        page.screenshot(path=shots / "sim-email-iphone.png", full_page=True)
        order_id = page.evaluate(f"window.DidiSim.myOrder('{number}').id")
        page.evaluate(
            """async (id) => {
              localStorage.setItem('didi-preview-admin', '1');
              await window.DidiSim.api("POST", `/api/v1/admin/orders/${id}/transition/`,
                { status: "cancelled", comment: "", notify: false });
              localStorage.removeItem('didi-preview-admin');
            }""",
            order_id,
        )
        page.goto(origin + f"{BASE}/me/profile/", wait_until="load")
        page.wait_for_selector(".tabbar .tab__icon .news-dot")
        page.goto(origin + f"{BASE}/me/orders/{number}/", wait_until="load")
        page.wait_for_selector(".page .h1")
        # Другие демо-заказы могут оставаться с отметкой — проверяем именно этот.
        page.goto(origin + f"{BASE}/me/orders/", wait_until="load")
        card = page.locator(f".order-card[href$='/orders/{number}/']")
        card.wait_for()
        assert card.locator(".news-dot").count() == 0, "точка не погасла после открытия заказа"
        print("B13: фото на весь экран, «Поделиться», смена email кодом, точка «есть новости»: ок")

        # 4. Скриншоты комнат.
        first_product = BASE + check["path"]
        for theme in ("light", "dark"):
            for device_name, device in (("iphone", IPHONE), ("desktop", DESKTOP)):
                page = page_for(device, theme)
                for name, path in SHOTS:
                    url = first_product if path is None else BASE + path
                    page.goto(origin + url, wait_until="load")
                    page.wait_for_timeout(300)
                    page.screenshot(path=shots / f"{name}-{device_name}-{theme}.png")
        # 5. Панель администратора (если собрана).
        if (site / "panel/preview-api.json").exists():
            check_panel(page_for, site, origin, shots, problems)
        browser.close()
    server.shutdown()

    if problems:
        print("Ошибки:\n" + "\n".join(sorted(set(problems))))
        sys.exit(1)
    print("Превью: ошибок нет")


PANEL_API = "/api/v1/admin"
# Фото для «Добавить пачкой»: 1×1 PNG — имитация всё равно перерисует его на canvas.
PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def panel_shots(site: Path) -> list[tuple[str, str]]:
    """(имя, адрес без BASE): экраны панели; id — из снимка API, как в build.py."""
    snapshot = json.loads((site / "panel/preview-api.json").read_text(encoding="utf-8"))

    def first(path: str) -> int:
        return snapshot[f"{PANEL_API}/{path}/"]["results"][0]["id"]

    online = next(
        (
            order["id"]
            for order in snapshot[f"{PANEL_API}/orders/"]["results"]
            if order["payment_method"] == "online"
        ),
        first("orders"),
    )
    return [
        ("summary", "/panel/"),
        ("orders", "/panel/orders/"),
        ("order", f"/panel/orders/{online}/"),
        ("products", "/panel/catalog/products/"),
        ("product", f"/panel/catalog/products/{first('catalog/products')}/"),
        ("batch", "/panel/catalog/products/batch/"),
        ("drafts", "/panel/catalog/products/drafts/"),
        ("categories", "/panel/catalog/categories/"),
        ("articles", "/panel/content/articles/"),
        ("customers", "/panel/customers/"),
        ("look-home", "/panel/look/home/"),
        ("look-panel", "/panel/look/panel/"),
        ("settings", "/panel/settings/"),
        ("account", "/panel/account/"),
        ("login", "/panel/login/"),
    ]


def check_panel_guards(page_for, site: Path, origin: str) -> None:
    """Панель: остаток нового товара, предупреждение о несохранённом, режим «Смотреть»."""
    page = page_for(DESKTOP, pages_404=True)
    asked: list[str] = []
    page.on("dialog", lambda dialog: asked.append(dialog.message))
    page.add_init_script("localStorage.setItem('didi-preview-admin', '1')")

    page.goto(origin + BASE + "/panel/catalog/products/new/", wait_until="load")
    page.fill("main input.pf-title", "Проверка остатка")
    page.locator("main select").first.select_option(index=1)
    page.get_by_label("Цена, ₽", exact=True).fill("1000")
    page.get_by_role("button", name="+ Одежда").click()
    assert page.get_by_label("Остаток нового товара", exact=True).input_value() == "1"
    page.get_by_role("button", name="Опубликовать").click()
    page.get_by_label("Остаток: S", exact=True).wait_for()
    assert page.get_by_label("Остаток: S", exact=True).input_value() == "1"
    assert not asked, f"создание товара спросило о несохранённом: {asked}"

    page.fill("main input.pf-title", "Проверка остатка 2")
    page.locator("nav.nav a", has_text="Заказы").click()
    page.locator("main h1", has_text="Заказы").wait_for()
    assert any("несохранённые" in text for text in asked), "переход не предупредил о несохранённом"

    page.go_back()
    size = page.get_by_label("Остаток: S", exact=True)
    size.wait_for()
    size.fill("-3")
    page.get_by_role("button", name="Сохранить", exact=True).click()
    page.locator("main .alert", has_text="Исправьте остатки").wait_for()
    size.fill("1")

    snapshot = json.loads((site / "panel/preview-api.json").read_text(encoding="utf-8"))
    orders = snapshot[f"{PANEL_API}/orders/"]["results"]
    pending = next(order["id"] for order in orders if order["status"] == "awaiting_agreement")
    viewer = page_for(DESKTOP)
    viewer.add_init_script("localStorage.setItem('didi-preview-admin', '1')")
    viewer.goto(origin + BASE + "/panel/", wait_until="load")
    viewer.locator("main h1").wait_for()
    viewer.evaluate(
        """() => {
          const key = "didi-sim-db-v2";
          const db = JSON.parse(localStorage.getItem(key));
          db.me.is_owner = false;
          for (const section in db.me.permissions) db.me.permissions[section] = "view";
          localStorage.setItem(key, JSON.stringify(db));
        }"""
    )
    viewer.goto(origin + BASE + f"/panel/orders/{pending}/", wait_until="load")
    cancel = viewer.get_by_role("button", name="Отменить заказ")
    cancel.wait_for()
    assert cancel.is_disabled(), "«Смотреть»: действие с заказом доступно"
    assert viewer.get_by_role("button", name="Назад").is_enabled(), "«Смотреть»: «Назад» отключена"
    viewer.goto(origin + BASE + "/panel/orders/", wait_until="load")
    box = viewer.locator("main tbody input[type=checkbox]").first
    box.wait_for(state="attached")
    assert box.is_disabled(), "«Смотреть»: заказы можно отметить"
    assert viewer.locator("main select").first.is_enabled(), "«Смотреть»: фильтр отключён"
    viewer.context.close()
    page.context.close()


def check_panel(page_for, site: Path, origin: str, shots: Path, problems: list[str]) -> None:
    # Вход администратора на странице «Вход» витрины → сводка панели.
    data = json.loads((site / "static/preview/data.json").read_text(encoding="utf-8"))
    page = page_for(IPHONE)
    page.goto(origin + BASE + "/login/", wait_until="load")
    page.fill('main input[name="email"]', data["admin"]["email"])
    page.fill('main input[name="password"]', data["admin"]["password"])
    page.click('main form[method="post"] button[type="submit"]')
    page.wait_for_url(f"**{BASE}/panel/")
    page.wait_for_selector("main h1:has-text('Сводка')")
    page.screenshot(path=shots / "panel-from-site-login-iphone.png")
    print("Вход администратора с витрины → панель: ок")

    # Цвета: связка двух товаров → переключатель на карточке, переход на второй цвет.
    linked = page.evaluate(
        """async () => {
          const url = "/api/v1/admin/catalog/products/";
          const list = await window.DidiSim.api("GET", url + "?status=active");
          const [a, b] = list.body.results;
          const items = [{ id: a.id, color_name: "Зелёный" }, { id: b.id, color_name: "Бежевый" }];
          const done = await window.DidiSim.api("POST", url + "colors/", { items });
          return { status: done.status, first: a.slug, second: b.slug };
        }"""
    )
    assert linked["status"] == 200, linked
    page.goto(f"{origin}{BASE}/product/{linked['first']}/", wait_until="load")
    page.wait_for_selector(".colors__list .color.is-on")
    assert page.locator(".colors__list .color").count() == 2
    page.screenshot(path=shots / "sim-product-colors-iphone.png")
    page.click(f'.colors__list .color[href$="/product/{linked["second"]}/"]')
    page.wait_for_selector(".colors__name:text-is('Бежевый')")
    page.goto(origin + BASE + "/panel/", wait_until="load")
    page.wait_for_selector("main h1:has-text('Сводка')")
    print("Цвета: связка и переключатель на карточке: ок")

    # Пароль сотрудника: смена в «Аккаунте» → выход → вход с новым; «Забыли пароль?» на входе
    # панели → сброс кодом на сайте → снова в панели. В конце пароль демо возвращается.
    admin = data["admin"]
    changed = admin["password"] + "-2"
    page.goto(origin + BASE + "/panel/account/", wait_until="load")
    page.wait_for_selector("main h1:has-text('Аккаунт')")
    form = page.locator("main form:has(input[autocomplete='new-password'])")
    form.locator("input[autocomplete='current-password']").fill(admin["password"])
    form.locator("input[autocomplete='new-password']").nth(0).fill(changed)
    form.locator("input[autocomplete='new-password']").nth(1).fill(changed)
    form.locator("button[type='submit']").click()
    try:
        page.wait_for_selector(".note-success:has-text('Пароль изменён')", timeout=10_000)
    except Exception as exc:
        errors = " | ".join(page.locator("main .alert, main .field-error").all_text_contents())
        raise AssertionError(f"Смена пароля в панели не прошла: {errors}") from exc
    page.screenshot(path=shots / "panel-account-iphone.png")
    page.evaluate("localStorage.removeItem('didi-preview-admin')")
    page.goto(origin + BASE + "/panel/login/", wait_until="load")
    page.fill(".login-card input[type='email']", admin["email"])
    page.fill(".login-card input[type='password']", admin["password"])
    page.click(".login-card button[type='submit']")
    page.wait_for_selector(".login-card .alert")  # старый пароль больше не подходит
    page.fill(".login-card input[type='password']", changed)
    page.click(".login-card button[type='submit']")
    # Переход внутри панели: адрес /panel без «/» — ждём экран, а не адрес.
    page.wait_for_selector("main h1:has-text('Сводка')")
    page.evaluate("localStorage.removeItem('didi-preview-admin')")
    page.goto(origin + BASE + "/panel/login/", wait_until="load")
    page.fill(".login-card input[type='email']", admin["email"])
    page.click(".login-links a:has-text('Забыли пароль?')")
    page.wait_for_url(f"**{BASE}/password-reset/**")
    page.wait_for_selector('main input[name="email"]:visible')  # имитация отрисовала страницу
    assert page.input_value('main input[name="email"]') == admin["email"]
    page.click('main form[method="post"] button[type="submit"]')
    page.wait_for_url(f"**{BASE}/password-reset/confirm/**")
    page.fill('main input[name="code"]', "123456")
    page.fill('main input[name="new_password"]', admin["password"])
    page.click('main form[method="post"] button[type="submit"]')
    page.wait_for_url(f"**{BASE}/panel/")
    page.wait_for_selector("main h1:has-text('Сводка')")
    print("Пароль сотрудника: смена в панели и сброс кодом: ок")

    # «Добавить товар»: одно фото — обычная карточка с этим фото; «Назад» — к списку товаров.
    page.goto(origin + BASE + "/panel/catalog/products/", wait_until="load")
    page.click("main .page-header a:has-text('Добавить товар')")
    page.wait_for_selector(".batch-drop")
    page.set_input_files(
        ".batch-drop input[type=file]",
        [{"name": "one.png", "mimeType": "image/png", "buffer": PIXEL_PNG}],
    )
    page.click(".batch-next .batch-cta:has-text('карточка товара')")
    page.wait_for_selector("main h1:has-text('Новый товар')")
    assert page.locator(".pending-photos .photo-tile").count() == 1, "фото не перешло в карточку"
    # Вставка ⌘V: картинка из буфера добавляется к фото карточки.
    page.evaluate(
        """async (png) => {
          const blob = await (await fetch(`data:image/png;base64,${png}`)).blob();
          const data = new DataTransfer();
          data.items.add(new File([blob], "paste.png", { type: "image/png" }));
          window.dispatchEvent(new ClipboardEvent("paste", { clipboardData: data }));
        }""",
        base64.b64encode(PIXEL_PNG).decode(),
    )
    page.wait_for_function("document.querySelectorAll('.pending-photos .photo-tile').length === 2")
    page.click("main .page-back")
    page.wait_for_selector(".batch-drop")
    print("Добавить товар: одно фото → карточка, вставка ⌘V, «Назад»: ок")

    # «Добавить товар» пачкой: 4 фото → по 2 подряд → категория второму товару, первому — на шаге
    # «Общее» → 2 черновика → цена одному → «Опубликовать готовые» → черновиком остался один.
    page.goto(origin + BASE + "/panel/catalog/products/batch/", wait_until="load")
    page.wait_for_selector(".batch-drop")
    page.set_input_files(
        ".batch-drop input[type=file]",
        [{"name": f"p{n}.png", "mimeType": "image/png", "buffer": PIXEL_PNG} for n in range(4)],
    )
    page.click(".batch-chip:has-text('По 2 подряд')")
    page.locator(".batch-tile").nth(2).click()
    assert page.locator(".batch-tile.is-selected").count() == 2, "товар выделяется целиком"
    page.click(".batch-action:has-text('Категория')")
    page.locator(".sheet-row").nth(0).click()
    page.screenshot(path=shots / "panel-batch-grid-iphone.png")
    page.click(".batch-next .batch-cta")
    page.wait_for_selector(".batch-common")
    rest = "[role=radiogroup][aria-label='Категория для остальных'] button"
    page.locator(f".batch-common {rest}").first.click()
    # Тип размеров: «Обувь жен.» — чипы «RU · US», таблица размеров в шторке.
    page.click("[aria-label='Тип размеров'] button:has-text('Обувь жен.')")
    chip = page.locator(".batch-option:has-text('38 · 8 US')")
    assert chip.get_attribute("aria-pressed") == "true", "38 · 8 US не отмечен по умолчанию"
    page.click(".batch-field-head button:has-text('Таблица размеров')")
    assert page.locator(".size-chart tbody tr").count() == 12, "в таблице размеров не 12 строк"
    page.screenshot(path=shots / "panel-batch-sizes-iphone.png")
    page.click(".sheet button:has-text('Закрыть')")
    page.click("[aria-label='Тип размеров'] button:has-text('Одежда')")
    page.click(".batch-next .batch-cta")
    page.wait_for_selector(".draft-card", timeout=30_000)
    assert page.locator(".draft-card").count() == 2, "черновиков не два"
    page.locator(".draft-check input").nth(0).check()
    page.fill("#mass-price", "1990")
    page.click(".batch-price button[type=submit]")
    page.wait_for_selector(".draft-card .badge-success")
    page.click(".batch-next .batch-cta")
    page.wait_for_selector(".note-success:has-text('Опубликовано: 1')")
    assert page.locator(".draft-card").count() == 1, "опубликованный остался в черновиках"
    page.screenshot(path=shots / "panel-batch-drafts-iphone.png")
    print("Товары пачкой: раскладка, категории, типы размеров, черновики, цена и публикация: ок")

    check_panel_guards(page_for, site, origin)

    screens = panel_shots(site)
    for theme in ("light", "dark"):
        for device_name, device in (("iphone", IPHONE), ("desktop", DESKTOP)):
            page = page_for(device)
            # Тема и «сессия» администратора превью (на странице входа — без неё).
            page.context.add_init_script(
                "try {"
                f" localStorage.setItem('didi-panel-theme', '{theme}');"
                " if (/\\/login\\/?$/.test(location.pathname))"
                " localStorage.removeItem('didi-preview-admin');"
                " else localStorage.setItem('didi-preview-admin', '1');"
                " } catch (e) {}"
            )
            for name, path in screens:
                page.goto(origin + BASE + path, wait_until="load")
                page.wait_for_selector(".login-card" if name == "login" else "main h1")
                page.wait_for_function(
                    "!document.body.innerText.includes('Загрузка…')"
                    " && !document.querySelector('.is-loading')"
                )
                page.wait_for_timeout(200)
                alerts = page.locator(".alert").all_text_contents()
                if alerts:
                    problems.append(f"{page.url}: {' | '.join(alerts)}")
                page.screenshot(path=shots / f"panel-{name}-{device_name}-{theme}.png")
            if device_name == "iphone":
                page.goto(origin + BASE + "/panel/orders/", wait_until="load")
                page.click(".mobilebar .icon-button")
                page.wait_for_timeout(400)
                page.screenshot(path=shots / f"panel-menu-iphone-{theme}.png")
    print(f"Панель: экранов проверено {len(screens)} × 4")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
