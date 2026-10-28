"""Проверка собранного превью в браузере (Playwright): каждая страница открывается без ошибок
в консоли и без битых ресурсов; имитация работает от начала до конца (товар → корзина → вход →
оформление → заказ виден в панели; новый товар из панели открывается в магазине); скриншоты
ключевых комнат на телефоне и десктопе в обеих темах. Панель администратора (`/panel/`) — каждый
экран открывается с данными, без сообщений об ошибке; скриншоты — panel-*.

    python deploy/preview/check.py _site shots
Сайт раздаётся локально по тому же пути, что на Pages (PREVIEW_BASE).
"""

import functools
import http.server
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

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

        # 2. Покупатель: товар → корзина (+1) → вход → оформление → страница заказа.
        page = page_for(IPHONE, pages_404=True)
        check = data["check"]
        page.goto(origin + BASE + check["path"], wait_until="load")
        page.click(f'label.sz:has(input[value="{check["variant"]}"])')
        page.click("[data-cta]")
        page.wait_for_selector("[data-added]")
        assert page.text_content("#cart-badge-tab").strip() == "1"
        page.goto(origin + f"{BASE}/cart/", wait_until="load")
        page.wait_for_selector(".lines .line")
        page.click('form[data-op="inc"] button')
        page.wait_for_selector(".stepper__value:text-is('2')")
        page.screenshot(path=shots / "sim-cart-iphone.png")
        page.click(".cta--link")  # гость → вход
        page.fill('main input[name="email"]', data["customer"]["email"])
        page.fill('main input[name="password"]', data["customer"]["password"])
        page.click('main form[method="post"] button[type="submit"]')
        page.wait_for_url(f"**{BASE}/me/checkout/")
        page.wait_for_selector(f".mini li:has-text('{check['name']}')")
        page.screenshot(path=shots / "sim-checkout-iphone.png", full_page=True)
        page.click("[data-checkout] button[type=submit]")
        page.wait_for_url(f"**{BASE}/me/orders/DD-*/")
        page.wait_for_selector(".page .h1:has-text('Заказ')")
        number = page.text_content(".page .h1 .nowrap").strip()
        assert page.evaluate("window.DidiSim.cartCount()") == 0
        page.screenshot(path=shots / "sim-order-iphone.png", full_page=True)
        print(f"Имитация: корзина и оформление — заказ {number}")

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
        ("categories", "/panel/catalog/categories/"),
        ("articles", "/panel/content/articles/"),
        ("customers", "/panel/customers/"),
        ("login", "/panel/login/"),
    ]


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
