"""Браузерный сценарий веб-витрины на развёрнутом магазине (Playwright, Chromium).

    python3 deploy/e2e_storefront.py https://localhost e2e-report/storefront

Телефон (iPhone, светлая тема): главная с фото → свёрнутая шапка → быстрый поиск из лаймовой
кнопки → результаты → товар → размер → «В корзину» (htmx, счётчик) → корзина гостя → оформление
→ вход → регистрация → оформление «при получении» → заказ → администратор видит его в панели
(заказы, товары, статьи, форма статьи) → покупатель отменяет заказ. Логотип — наверх коротким
путём. Тёмная тема (prefers-color-scheme) и переключатель в шапке. Вкладка «Контакты»: мессенджеры,
статьи, страница статьи. Десктоп в обеих темах: верхняя навигация, сетка 4 колонки, карточка
товара в две колонки, контакты.
Любое сообщение об ошибке в консоли (в т.ч. нарушение CSP) — провал. Скриншоты — в папку отчёта.
Нужен администратор из .env (ADMIN_EMAIL/ADMIN_PASSWORD).

Установка: pip install playwright && python -m playwright install --with-deps chromium
"""

import json
import os
import re
import sys
import uuid
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

TIMEOUT_MS = 30_000
expect.set_options(timeout=TIMEOUT_MS)
IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)
PASSWORD = "E2e-Shopper-Passw0rd"


def env_value(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    env = Path(__file__).resolve().parent.parent / ".env"
    for line in env.read_text(encoding="utf-8").splitlines() if env.exists() else []:
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return ""


class Report:
    def __init__(self, out: Path):
        self.out = out
        self.step = 0
        out.mkdir(parents=True, exist_ok=True)

    def shot(self, page: Page, name: str, full: bool = False) -> None:
        self.step += 1
        page.wait_for_timeout(450)  # анимации шапки и появления блоков
        page.screenshot(path=self.out / f"{self.step:02d}-{name}.png", full_page=full)
        print(f"ok   {self.step:02d} {name}")


def watch_console(page: Page, errors: list[str]) -> None:
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))


def wait_until(page: Page, script: str, arg=None, what: str = "условие") -> None:
    """Опрос через evaluate: wait_for_function использует eval, а CSP витрины его запрещает
    (так и должно быть — проверяем страницу с боевыми заголовками)."""
    for _ in range(TIMEOUT_MS // 250):
        if page.evaluate(script, arg):
            return
        page.wait_for_timeout(250)
    raise AssertionError(f"не дождались: {what}")


def wait_photos(page: Page, minimum: int) -> None:
    """Ждём фото на видимой части экрана: нижние грузятся лениво (loading=lazy), и при ожидании
    «N фото на странице» проверка зависела от того, успел ли браузер дотянуть дальние."""
    wait_until(
        page,
        """(n) => {
            const shown = [...document.images].filter((img) => {
                const r = img.getBoundingClientRect();
                return r.width > 0 && r.bottom > 0 && r.top < innerHeight
                    && (img.currentSrc || img.src).includes('/media/');
            });
            return shown.length >= n && shown.every((img) => img.complete && img.naturalWidth > 0);
        }""",
        minimum,
        f"{minimum} фото на экране",
    )


def phone(browser, scheme: str):
    return browser.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        user_agent=IPHONE_UA,
        ignore_https_errors=True,
        color_scheme=scheme,
        locale="ru-RU",
    )


def desktop(browser, scheme: str):
    return browser.new_context(
        viewport={"width": 1440, "height": 900},
        ignore_https_errors=True,
        color_scheme=scheme,
        locale="ru-RU",
    )


def in_stock_product(page: Page) -> None:
    page.locator(".grid .card:not(:has(.soldout))").first.click()
    page.wait_for_load_state("networkidle")


def pick_size(page: Page) -> None:
    sizes = page.locator(".sz:not(.is-off) input")
    if sizes.count():
        sizes.first.check(force=True)


def seo_checks(page: Page, base: str) -> None:
    raw = page.locator('script[type="application/ld+json"]').inner_text()
    data = json.loads(raw)
    assert data["@type"] == "Product" and data["offers"]["priceCurrency"] == "RUB", data
    assert re.fullmatch(r"\d+\.\d{2}", data["offers"]["price"]), data["offers"]
    canonical = page.locator('link[rel="canonical"]').get_attribute("href")
    assert canonical.startswith(base + "/product/"), canonical


def shopper(browser, base: str, report: Report, errors: list[str]) -> None:
    context = phone(browser, "light")
    page = context.new_page()
    watch_console(page, errors)

    page.goto(base + "/")
    wait_photos(page, 4)
    expect(page.locator("[data-header]")).not_to_have_class(re.compile("is-compact"))
    report.shot(page, "phone-home")
    # Баннер приложения на телефоне: закрывается и больше не показывается.
    banner = page.locator("[data-banner]")
    expect(banner).to_be_visible()
    banner.get_by_role("button", name="Закрыть").click()
    expect(banner).to_have_count(0)

    page.mouse.wheel(0, 1600)
    expect(page.locator("[data-header]")).to_have_class(re.compile("is-compact"))
    report.shot(page, "phone-header-compact")
    scrolled = page.evaluate("scrollY")

    # Быстрый поиск: поле выезжает в строке шапки, страница не прокручивается.
    page.click("[data-quick-open]")
    quick = page.get_by_label("Быстрый поиск")
    expect(quick).to_be_focused()
    assert page.evaluate("scrollY") == scrolled, "быстрый поиск прокрутил страницу"
    report.shot(page, "phone-quick-search")
    quick.fill("кеды")
    quick.press("Enter")
    page.wait_for_url(re.compile(r"/search/\?q="))
    expect(page.locator(".grid .card").first).to_be_visible()
    report.shot(page, "phone-search-results")

    # Логотип с главной — наверх коротким путём.
    page.goto(base + "/")
    page.mouse.wheel(0, 3000)
    page.wait_for_timeout(300)
    page.click("[data-to-top]")
    wait_until(page, "() => scrollY === 0", what="возврат наверх по логотипу")

    page.locator(".cats .seg").nth(1).click()
    page.wait_for_url(re.compile(r"/category/"))
    report.shot(page, "phone-category")
    in_stock_product(page)
    seo_checks(page, base)
    report.shot(page, "phone-product")
    pick_size(page)
    page.click("[data-cta]")
    expect(page.locator("[data-added]")).to_be_visible()
    expect(page.locator("#cart-badge-tab")).to_have_text("1")
    report.shot(page, "phone-added-to-cart")

    page.locator(".tabbar a[href='/cart/']").click()
    expect(page.locator(".line")).to_have_count(1)
    page.locator(".stepper form").nth(1).locator("button").click()  # +1 (htmx)
    expect(page.locator(".stepper__value")).to_have_text("2")
    report.shot(page, "phone-cart-guest")

    # Гость → вход → регистрация (корзина переносится) → оформление.
    page.click("a.cta[href='/checkout/']")
    page.wait_for_url(re.compile(r"/login/\?next="))
    page.get_by_role("link", name="Регистрация").click()
    email = f"web-{uuid.uuid4().hex[:8]}@example.com"
    page.get_by_label("Имя").fill("Покупатель")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Пароль").fill(PASSWORD)
    page.locator('input[name="consent"]').check()
    report.shot(page, "phone-register")
    page.get_by_role("button", name="Зарегистрироваться").click()
    page.wait_for_url(re.compile(r"/checkout/$"))
    expect(page.locator(".mini li")).to_have_count(1)
    page.get_by_label("Телефон").fill("+7 900 123-45-67")
    page.get_by_label("Адрес доставки").fill("Москва, ул. Тестовая, 1, кв. 1")
    page.locator('input[name="payment_method"][value="on_delivery"]').check()
    report.shot(page, "phone-checkout", full=True)
    page.get_by_role("button", name="Оформить заказ").click()
    page.wait_for_url(re.compile(r"/orders/DD-\d+/$"))
    expect(page.locator(".status").first).to_have_text("Принят")
    expect(page.locator("#cart-badge-tab")).to_be_hidden()
    report.shot(page, "phone-order")
    number = re.search(r"/orders/(DD-\d+)/", page.url).group(1)
    admin_sees_order(browser, base, number, report)

    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="Отменить заказ").click()
    expect(page.locator(".status").first).to_have_text("Отменён")
    report.shot(page, "phone-order-cancelled")

    page.goto(base + "/orders/")
    expect(page.locator(".order-card")).to_have_count(1)
    report.shot(page, "phone-my-orders")
    context.close()


def admin_sees_order(browser, base: str, number: str, report: Report) -> None:
    # Консоль панели не проверяется: до входа она штатно получает 401 на auth/me/.
    context = browser.new_context(viewport={"width": 1280, "height": 800}, ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    page.goto(base + "/panel/")
    page.get_by_label("Email").fill(env_value("ADMIN_EMAIL"))
    page.get_by_label("Пароль").fill(env_value("ADMIN_PASSWORD"))
    page.get_by_role("button", name="Войти", exact=True).click()
    expect(page.get_by_role("button", name="Выйти")).to_be_visible()
    page.goto(base + "/panel/orders")
    expect(page.get_by_text(number).first).to_be_visible()
    report.shot(page, "panel-orders")
    page.goto(base + "/panel/catalog/products")
    page.wait_for_load_state("networkidle")
    report.shot(page, "panel-products")
    page.goto(base + "/panel/content/articles")
    expect(page.get_by_role("link", name="Как выбрать размер одежды")).to_be_visible()
    report.shot(page, "panel-articles")
    page.get_by_role("link", name="Как выбрать размер одежды").click()
    expect(page.get_by_label("Заголовок")).to_have_value("Как выбрать размер одежды")
    page.wait_for_load_state("networkidle")
    report.shot(page, "panel-article-edit")
    context.close()


def dark_phone(browser, base: str, report: Report, errors: list[str]) -> None:
    context = phone(browser, "dark")
    page = context.new_page()
    watch_console(page, errors)
    page.goto(base + "/")
    wait_photos(page, 4)
    report.shot(page, "phone-dark-home")
    page.mouse.wheel(0, 1600)
    expect(page.locator("[data-header]")).to_have_class(re.compile("is-compact"))
    report.shot(page, "phone-dark-header-compact")
    page.goto(base + "/products/")
    in_stock_product(page)
    report.shot(page, "phone-dark-product")
    pick_size(page)
    page.click("[data-cta]")
    expect(page.locator("[data-cta]")).to_have_class(re.compile("is-done"))
    page.goto(base + "/cart/")
    report.shot(page, "phone-dark-cart")
    # Переключатель в шапке: из системной тёмной — явно светлая, без перезагрузки, в cookie.
    page.get_by_role("button", name="Сменить тему").click()
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    report.shot(page, "phone-theme-switched-light")
    context.close()


def contacts(browser, base: str, report: Report, errors: list[str]) -> None:
    """Вкладка «Контакты»: каналы из .env, статьи, страница статьи; профиль — «Помощь»."""
    for scheme in ("light", "dark"):
        context = phone(browser, scheme)
        page = context.new_page()
        watch_console(page, errors)
        page.goto(base + "/")
        page.locator(".tabbar a[href='/contacts/']").click()
        page.wait_for_url(re.compile(r"/contacts/$"))
        expect(page.locator(".channel[href='https://t.me/didishop']")).to_be_visible()
        expect(page.locator(".channel[href='https://wa.me/79001234567']")).to_be_visible()
        expect(page.locator(".article-card")).not_to_have_count(0)
        page.wait_for_timeout(400)  # каналы появляются по очереди (до 0,7 с)
        report.shot(page, f"phone-{scheme}-contacts", full=True)
        page.locator(".article-card").first.click()
        page.wait_for_url(re.compile(r"/articles/"))
        expect(page.locator(".post__body p").first).to_be_visible()
        wait_photos(page, 1)
        report.shot(page, f"phone-{scheme}-article", full=True)
        page.goto(base + "/profile/")
        expect(page.locator("nav[aria-label='Помощь']")).to_be_visible()
        context.close()


def wide(browser, base: str, report: Report, errors: list[str]) -> None:
    for scheme in ("light", "dark"):
        context = desktop(browser, scheme)
        page = context.new_page()
        watch_console(page, errors)
        page.goto(base + "/")
        wait_photos(page, 4)
        expect(page.locator(".topnav")).to_be_visible()
        expect(page.locator(".tabbar")).to_be_hidden()
        columns = page.locator(".grid").evaluate(
            "(el) => getComputedStyle(el).gridTemplateColumns.split(' ').length"
        )
        assert columns == 4, f"на десктопе {columns} колонок"
        report.shot(page, f"desktop-{scheme}-home")
        page.locator(".cats .seg").nth(2).click()
        page.wait_for_url(re.compile(r"/category/"))
        report.shot(page, f"desktop-{scheme}-category")
        in_stock_product(page)
        report.shot(page, f"desktop-{scheme}-product")
        page.locator(".topnav a[href='/contacts/']").click()
        page.wait_for_url(re.compile(r"/contacts/$"))
        wait_photos(page, 1)
        report.shot(page, f"desktop-{scheme}-contacts")
        context.close()


def main() -> int:
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://localhost"
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "e2e-report/storefront")
    report = Report(out)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            shopper(browser, base, report, errors)
            dark_phone(browser, base, report, errors)
            contacts(browser, base, report, errors)
            wide(browser, base, report, errors)
        finally:
            browser.close()
    if errors:
        print("Ошибки в консоли браузера:", *errors, sep="\n  ")
        return 1
    print("Витрина: сценарий покупателя пройден, ошибок в консоли нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
