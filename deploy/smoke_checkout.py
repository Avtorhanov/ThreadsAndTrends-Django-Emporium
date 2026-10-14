"""Нагрузочный smoke-тест оформления заказа: N покупателей одновременно покупают
последние единицы одного товара.

    python3 deploy/smoke_checkout.py https://shop.example.ru [--users 8] [--insecure]
    ./deploy.sh smoke [--users 8]

Проверяет: нет ошибок 5xx, заказов ровно столько, сколько было единиц товара (остаток не
уходит в минус и не продаётся дважды), остальные получают понятный отказ, повтор с тем же
Idempotency-Key не создаёт второй заказ; печатает время ответа (p50/p95).
Создаёт тестовых покупателей smoke-<id>@example.com и заказы «оплата при получении» —
после проверки отмените их в панели. Регистрация ограничена 10 в час с одного IP
(THROTTLE_AUTH_REGISTER), поэтому по умолчанию 8 покупателей.

Нужен администратор (ADMIN_EMAIL/ADMIN_PASSWORD из .env): тест ставит товару остаток.
Только стандартная библиотека Python.
"""

import argparse
import concurrent.futures
import http.cookiejar
import json
import os
import ssl
import statistics
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


class Client:
    def __init__(self, base: str, insecure: bool):
        self.base = base.rstrip("/")
        context = ssl.create_default_context()
        if insecure:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context),
            urllib.request.HTTPCookieProcessor(self.jar),
        )
        self.token = None
        self.timings: list[float] = []

    def call(self, method: str, path: str, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        request.add_header("Referer", self.base + "/")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        csrf = next((c.value for c in self.jar if c.name == "csrftoken"), None)
        if csrf:
            request.add_header("X-CSRFToken", csrf)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        started = time.perf_counter()
        try:
            with self.opener.open(request, timeout=60) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
        self.timings.append(time.perf_counter() - started)
        try:
            payload = json.loads(raw) if raw else None
        except ValueError:
            payload = raw[:200]
        return status, payload


def env_value(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def buyer(base: str, insecure: bool, variant_id: int, run: str, n: int) -> dict:
    client = Client(base, insecure)
    email = f"smoke-{run}-{n}@example.com"
    status, data = client.call(
        "POST", "/api/v1/auth/register/", {"email": email, "password": f"Smoke-{run}-Pass!{n}"}
    )
    if status != 201:
        return {"stage": "register", "status": status, "data": data, "timings": client.timings}
    client.token = data["access"]
    status, data = client.call("POST", "/api/v1/cart/items/", {"variant_id": variant_id})
    if status != 201:
        return {"stage": "cart", "status": status, "data": data, "timings": client.timings}
    total = data["total_kopecks"]
    key = uuid.uuid4().hex
    order = {
        "delivery_method": "courier",
        "payment_method": "on_delivery",
        "recipient_name": f"Smoke {n}",
        "recipient_phone": "+79990000000",
        "delivery_address": "Москва, ул. Тестовая, 1",
        "comment": "smoke-тест, отменить",
        "expected_total_kopecks": None,
    }
    status, data = client.call("POST", "/api/v1/orders/", order, {"Idempotency-Key": key})
    result = {"stage": "checkout", "status": status, "data": data, "timings": client.timings}
    if status == 201:
        # Повтор с тем же ключом — тот же заказ (200), не второй.
        again, repeat = client.call("POST", "/api/v1/orders/", order, {"Idempotency-Key": key})
        result["repeat_ok"] = again == 200 and repeat.get("number") == data.get("number")
        result["cart_total"] = total
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("base", help="Адрес сайта, например https://shop.example.ru")
    parser.add_argument("--users", type=int, default=8)
    parser.add_argument("--stock", type=int, default=3, help="Сколько единиц товара в продаже")
    parser.add_argument("--insecure", action="store_true", help="Не проверять сертификат")
    args = parser.parse_args()
    insecure = args.insecure or "://localhost" in args.base

    admin = Client(args.base, insecure)
    admin.call("GET", "/api/v1/admin/auth/csrf/")
    status, _ = admin.call(
        "POST",
        "/api/v1/admin/auth/login/",
        {"email": env_value("ADMIN_EMAIL"), "password": env_value("ADMIN_PASSWORD")},
    )
    if status != 200:
        print(f"Не удалось войти администратором ({status}). Задайте ADMIN_EMAIL/ADMIN_PASSWORD.")
        return 1

    # Отдельный товар для теста: остаток --stock, дальше — гонка покупателей.
    status, categories = admin.call("GET", "/api/v1/admin/catalog/categories/?page_size=100")
    rows = categories["results"] if isinstance(categories, dict) else categories
    leaf = next(c for c in rows if c["parent"] is not None)
    run = uuid.uuid4().hex[:6]
    status, product = admin.call(
        "POST",
        "/api/v1/admin/catalog/products/",
        {
            "name": f"Smoke-тест {run}",
            "category": leaf["id"],
            "price_kopecks": 100_00,
            "description": "Товар нагрузочного теста, удалите после проверки",
            "is_active": True,
            "variants": [{"size": "", "stock": args.stock}],
        },
    )
    if status != 201:
        print(f"Не удалось создать тестовый товар ({status}): {product}")
        return 1
    variant_id = product["variants"][0]["id"]

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.users) as pool:
        futures = [
            pool.submit(buyer, args.base, insecure, variant_id, run, n) for n in range(args.users)
        ]
        results = [f.result() for f in futures]
    elapsed = time.perf_counter() - started

    status, product_after = admin.call("GET", f"/api/v1/admin/catalog/products/{product['id']}/")
    stock_left = product_after["variants"][0]["stock"]
    admin.call("DELETE", f"/api/v1/admin/catalog/products/{product['id']}/")

    timings = sorted(t for r in results for t in r["timings"])
    created = [r for r in results if r["stage"] == "checkout" and r["status"] == 201]
    refused = [r for r in results if r["status"] in (400, 409)]
    server_errors = [r for r in results if r["status"] >= 500]
    other = [r for r in results if r not in created and r not in refused]
    expected = min(args.stock, args.users)

    print(f"Покупателей: {args.users}, единиц в продаже: {args.stock}, время: {elapsed:.1f} с")
    print(f"Заказов: {len(created)} (ожидалось {expected}), отказов «нет в наличии»: {len(refused)}")
    print(f"Остаток после теста: {stock_left} (ожидалось {args.stock - len(created)})")
    if timings:
        p95 = timings[max(0, int(len(timings) * 0.95) - 1)]
        print(f"Запросов: {len(timings)}, p50 {statistics.median(timings) * 1000:.0f} мс, "
              f"p95 {p95 * 1000:.0f} мс, max {timings[-1] * 1000:.0f} мс")
    for r in other:
        print(f"  этап {r['stage']}: {r['status']} {r.get('data')}")

    ok = (
        not server_errors
        and len(created) == expected
        and stock_left == args.stock - len(created)
        and all(r.get("repeat_ok") for r in created)
        and not [r for r in other if r["stage"] != "checkout"]
    )
    print("SMOKE OK" if ok else "SMOKE FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
