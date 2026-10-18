"""Браузерный сценарий на развёрнутом магазине (Playwright, Chromium).

    python3 deploy/e2e_browser.py https://localhost e2e-report

Покупатель на iPhone (веб-версия): каталог с фото и подсказкой установки → поиск → товар →
размер → корзина → регистрация → оформление «при получении» → заказ. Администратор видит
заказ в панели. Покупатель отменяет заказ. Широкий экран: сетка товаров с фото.
Скриншоты каждого шага — в папке отчёта. Нужен администратор из .env (ADMIN_EMAIL/PASSWORD).

Установка: pip install playwright && python -m playwright install --with-deps chromium
"""

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
SIZES = ["41", "42", "40", "39", "M", "L", "S"]


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

    def shot(self, page: Page, name: str) -> None:
        self.step += 1
        page.screenshot(path=self.out / f"{self.step:02d}-{name}.png")
        print(f"ok   {self.step:02d} {name}")


def loaded_images(page: Page) -> int:
    """Сколько фото товаров реально загрузилось (а не просто есть в разметке)."""
    return page.evaluate(
        """() => [...document.images].filter(
            (img) => img.src.includes('/media/') && img.complete && img.naturalWidth > 0
        ).length"""
    )


def wait_images(page: Page, minimum: int) -> int:
    page.wait_for_function(
        """(n) => [...document.images].filter(
            (img) => img.src.includes('/media/') && img.complete && img.naturalWidth > 0
        ).length >= n""",
        arg=minimum,
        timeout=TIMEOUT_MS,
    )
    return loaded_images(page)


def shopper(browser, base: str, report: Report):
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        user_agent=IPHONE_UA,
        ignore_https_errors=True,
        locale="ru-RU",
    )
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    # 1. Каталог: категории, поиск, подсказка «На экран Домой» для iPhone.
    page.goto(base + "/")
    expect(page.get_by_text("Все товары", exact=True)).to_be_visible()
    expect(page.get_by_text("Установите магазин на телефон")).to_be_visible()
    report.shot(page, "iphone-catalog")

    # 2. Поиск по русской морфологии и началу слова.
    search = page.get_by_label("Поиск товаров")
    search.fill("кроссовк")
    search.press("Enter")
    expect(page.get_by_text(re.compile(r"Найдено товаров: [1-9]"))).to_be_visible()
    print(f"     фото в выдаче: {wait_images(page, 1)}")
    report.shot(page, "iphone-search")

    # 3. Карточка товара: галерея, размер, «В корзину».
    page.get_by_role("button", name=re.compile("Кроссовки")).first.click()
    expect(page.get_by_text("Размер", exact=True)).to_be_visible()
    wait_images(page, 1)
    for size in SIZES:
        chip = page.get_by_role("button", name=size, exact=True)
        if chip.count() and chip.first.is_enabled():
            chip.first.click()
            break
    page.get_by_role("button", name="В корзину", exact=True).click()
    expect(page.get_by_text("Товар в корзине.")).to_be_visible()
    report.shot(page, "iphone-product")

    # 4. Корзина гостя → вход → регистрация.
    page.get_by_text("Перейти в корзину").click()
    expect(page.get_by_role("button", name="Войти и оформить")).to_be_visible()
    report.shot(page, "iphone-cart")
    page.get_by_role("button", name="Войти и оформить").click()
    page.get_by_text("Нет аккаунта? Зарегистрироваться").click()
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    password = f"E2e-{uuid.uuid4().hex[:10]}"
    page.get_by_label("Email").fill(email)
    page.get_by_label("Имя", exact=True).fill("Анна")
    page.get_by_label("Фамилия").fill("Тестова")
    page.get_by_label("Пароль", exact=True).fill(password)
    page.get_by_label("Повторите пароль").fill(password)
    page.get_by_role("button", name="Создать аккаунт").click()

    # После регистрации гостевая корзина переносится в аккаунт.
    checkout = page.get_by_role("button", name="Оформить заказ", exact=True)
    checkout.wait_for()
    checkout.click()

    # 5. Оформление: курьер, оплата при получении.
    expect(page.get_by_text("Получатель", exact=True)).to_be_visible()
    page.get_by_label("Имя и фамилия").fill("Анна Тестова")
    page.get_by_label("Телефон").fill("+7 900 123-45-67")
    page.get_by_label("Адрес доставки").fill("Москва, ул. Тестовая, д. 1, кв. 2")
    page.get_by_role("radio", name=re.compile("При получении")).click()
    report.shot(page, "iphone-checkout")
    page.get_by_role("button", name=re.compile("Подтвердить заказ")).click()
    page.wait_for_url(re.compile(r"/orders/DD-\d+"))
    number = re.search(r"/orders/(DD-\d+)", page.url).group(1)
    expect(page.get_by_role("button", name="Отменить заказ")).to_be_visible()
    report.shot(page, "iphone-order")
    print(f"     заказ {number}, покупатель {email}")

    assert not errors, f"ошибки JavaScript: {errors}"
    return number, page, context


def admin_sees_order(browser, base: str, number: str, report: Report) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 800}, ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    page.goto(base + "/panel/")
    page.get_by_label("Email").fill(env_value("ADMIN_EMAIL"))
    page.get_by_label("Пароль").fill(env_value("ADMIN_PASSWORD"))
    page.get_by_role("button", name="Войти", exact=True).click()
    expect(page.get_by_text(number).first).to_be_visible()
    report.shot(page, "panel-orders")
    page.goto(base + "/panel/catalog/products")
    page.wait_for_load_state("networkidle")
    report.shot(page, "panel-products")
    context.close()


def desktop_grid(browser, base: str, report: Report) -> None:
    context = browser.new_context(viewport={"width": 1280, "height": 900}, ignore_https_errors=True)
    page = context.new_page()
    page.set_default_timeout(TIMEOUT_MS)
    page.goto(base + "/")
    page.get_by_text("Все товары", exact=True).click()
    expect(page.get_by_text(re.compile(r"Найдено товаров: \d+"))).to_be_visible()
    count = wait_images(page, 8)
    print(f"     фото на широком экране: {count}")
    report.shot(page, "desktop-products")
    context.close()


def main() -> int:
    base, out = sys.argv[1].rstrip("/"), Path(sys.argv[2] if len(sys.argv) > 2 else "e2e-report")
    report = Report(out)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        number, page, context = shopper(browser, base, report)
        admin_sees_order(browser, base, number, report)

        # 6. Покупатель отменяет заказ (подтверждение — системный диалог браузера).
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Отменить заказ").click()
        expect(page.get_by_text("Отменён").first).to_be_visible()
        report.shot(page, "iphone-order-cancelled")
        context.close()

        desktop_grid(browser, base, report)
        browser.close()
    print("BROWSER E2E OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
