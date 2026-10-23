"""Проверка собранного превью в браузере (Playwright): каждая страница открывается без ошибок
в консоли и без битых ресурсов, имитация корзины и оформления работает; скриншоты ключевых
комнат на телефоне и десктопе в обеих темах. Панель администратора (`/panel/`) — каждый экран
открывается с данными из снимка API, без сообщений об ошибке; скриншоты — panel-*.

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
    def log_message(self, *args):
        pass


def serve(site: Path) -> tuple[str, http.server.ThreadingHTTPServer]:
    """Раздать папку сайта под путём BASE (как project site на github.io)."""
    holder = Path(tempfile.mkdtemp())
    target = holder / BASE.strip("/") if BASE else holder
    if BASE:
        target.symlink_to(site.resolve(), target_is_directory=True)
    else:
        holder = site.resolve()
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

        def page_for(device, theme=None):
            context = browser.new_context(**device, locale="ru-RU")
            if theme:
                context.add_cookies([{"name": "theme", "value": theme, "url": origin}])
            page = context.new_page()
            page.on(
                "console",
                lambda msg: msg.type == "error" and problems.append(f"{page.url}: {msg.text}"),
            )
            page.on("pageerror", lambda exc: problems.append(f"{page.url}: {exc}"))
            page.on(
                "response",
                lambda r: r.status >= 400 and problems.append(f"{r.status} {r.url}"),
            )
            return page

        # 1. Все страницы открываются чисто.
        page = page_for(DESKTOP)
        for path in data["pages"] + [f"{BASE}/rooms/"]:
            page.goto(origin + path, wait_until="load")
        print(f"Страниц проверено: {len(data['pages']) + 1}")

        # 2. Имитация: в корзину → корзина (+1) → оформление → «заказ оформлен».
        page = page_for(IPHONE)
        variant_id, variant = next(
            (k, v) for k, v in data["variants"].items() if v["size"] and v["max"] > 1
        )
        product = find_product_page(site, data, variant_id)
        page.goto(origin + product, wait_until="load")
        page.click(f'label.sz:has(input[value="{variant_id}"])')
        page.click("[data-cta]")
        page.wait_for_selector("[data-added]")
        assert page.text_content("#cart-badge-tab").strip() == "1"
        page.goto(origin + f"{BASE}/cart/", wait_until="load")
        page.wait_for_selector(".lines .line")
        page.click('form[data-op="inc"] button')
        page.wait_for_function(
            "document.querySelector('.stepper__value').textContent.trim() === '2'"
        )
        page.screenshot(path=shots / "sim-cart-iphone.png")
        page.click(".cta--link")  # гость → вход
        page.fill('main input[name="email"]', "anna@example.ru")
        page.fill('main input[name="password"]', "Preview-Passw0rd!")
        page.click('main form[method="post"] button[type="submit"]')
        page.wait_for_url(f"**{BASE}/me/checkout/")
        page.wait_for_function("document.querySelector('.mini li') !== null")
        assert variant["name"] in page.text_content(".mini")
        page.screenshot(path=shots / "sim-checkout-iphone.png", full_page=True)
        page.click("[data-checkout] button[type=submit]")
        page.wait_for_url(f"**{BASE}/me/orders/placed*/")
        assert page.evaluate("localStorage.getItem('didi-preview-cart')") == "[]"
        print("Имитация корзины и оформления: ок")

        # 3. Скриншоты комнат.
        first_product = find_product_page(site, data, variant_id)
        for theme in ("light", "dark"):
            for device_name, device in (("iphone", IPHONE), ("desktop", DESKTOP)):
                page = page_for(device, theme)
                for name, path in SHOTS:
                    url = first_product if path is None else BASE + path
                    page.goto(origin + url, wait_until="load")
                    page.wait_for_timeout(300)
                    page.screenshot(path=shots / f"{name}-{device_name}-{theme}.png")
        # 4. Панель администратора (если собрана).
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
    screens = panel_shots(site)
    for theme in ("light", "dark"):
        for device_name, device in (("iphone", IPHONE), ("desktop", DESKTOP)):
            page = page_for(device)
            page.context.add_init_script(
                f"try {{ localStorage.setItem('didi-panel-theme', '{theme}') }} catch (e) {{}}"
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


def find_product_page(site: Path, data: dict, variant_id: str) -> str:
    marker = f'name="variant" value="{variant_id}"'
    for path in data["pages"]:
        if "/product/" in path and not path.startswith(f"{BASE}/me/"):
            file = site / path[len(BASE) :].strip("/") / "index.html"
            if marker in file.read_text(encoding="utf-8"):
                return path
    raise AssertionError(f"нет страницы товара с вариантом {variant_id}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
