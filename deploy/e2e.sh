#!/usr/bin/env bash
# E2E продакшен-стека на чистой машине с Docker (CI или свой компьютер):
#
#   bash deploy/e2e.sh [папка-отчёта]
#
# 1. ./deploy.sh с DOMAIN=localhost — та же команда, что на сервере;
# 2. HTTPS, редирект с HTTP, заголовки безопасности, PWA (манифест, иконки), панель;
# 3. демо-каталог: товары с фото, каждое фото отдаётся;
# 4. manage.py check --deploy внутри контейнера;
# 5. нагрузочный smoke оформления (deploy/smoke_checkout.py);
# 6. бэкап и восстановление из него;
# 7. браузерный сценарий покупателя и администратора (deploy/e2e_browser.py, скриншоты).
#
# Внимание: перезаписывает .env и данные стека в этой папке. Не запускайте на сервере магазина.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=$(mkdir -p "${1:-e2e-report}" && cd "${1:-e2e-report}" && pwd)
BASE=https://localhost
COMPOSE=(docker compose -f compose.prod.yml)

step() { printf '\n\033[1;34m### %s\033[0m\n' "$*"; }
fail() {
  printf '\n\033[1;31mE2E FAILED: %s\033[0m\n' "$*" >&2
  "${COMPOSE[@]}" ps >&2 || true
  # В GitHub Actions — аннотация с причиной и хвостом логов (видна без доступа к логам job).
  if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
    local tail
    tail=$("${COMPOSE[@]}" logs --no-color --tail 25 app caddy 2>&1 | tail -n 40 | sed 's/%/%25/g' | sed ':a;N;$!ba;s/\n/%0A/g')
    echo "::error title=E2E: $*::$tail"
  fi
  exit 1
}
k() { curl -fsS --max-time 30 -k "$@"; }

[ ! -f .env ] || grep -q '^DOMAIN=localhost$' .env || fail ".env уже есть и это не тестовый стенд — e2e не запускается."

step "Деплой одной командой (DOMAIN=localhost)"
rm -f .env .deployed-domain
cp .env.prod.example .env
sed -i \
  -e 's/^DOMAIN=.*/DOMAIN=localhost/' \
  -e 's/^ADMIN_EMAIL=.*/ADMIN_EMAIL=admin@example.com/' \
  -e 's/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=E2e-admin-Passw0rd/' \
  -e 's/^SEED_DEMO=.*/SEED_DEMO=1/' \
  .env
echo "GUNICORN_WORKERS=2" >> .env
./deploy.sh </dev/null 2>&1 | tee "$OUT/deploy.log" || fail "deploy.sh завершился с ошибкой"

step "HTTPS, редирект, заголовки"
k "$BASE/api/v1/health/" | tee "$OUT/health.json"; echo
code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost/)
[ "$code" = "308" ] || fail "http:// не перенаправляет на https:// (код $code)"
headers=$(k -I "$BASE/")
grep -qi '^strict-transport-security:' <<<"$headers" || fail "нет HSTS"
grep -qi '^content-security-policy:' <<<"$headers" || fail "нет CSP у витрины"

step "Витрина как приложение (PWA) и панель"
# Ответы — в переменные: `curl | grep -q` под pipefail ловит SIGPIPE.
html=$(k "$BASE/")
grep -q 'manifest.webmanifest' <<<"$html" || fail "в index.html нет манифеста"
grep -q 'apple-touch-icon' <<<"$html" || fail "в index.html нет иконки для iPhone"
manifest_headers=$(k -I "$BASE/manifest.webmanifest")
grep -qi 'content-type: application/manifest+json' <<<"$manifest_headers" || fail "манифест отдаётся не как application/manifest+json"
k "$BASE/manifest.webmanifest" | python3 -c 'import json,sys; m=json.load(sys.stdin); assert m["display"]=="standalone" and len(m["icons"])>=2'
for icon in apple-touch-icon.png icon-192.png icon-512.png; do
  k -o /dev/null "$BASE/icons/$icon" || fail "нет иконки $icon"
done
spa=$(k "$BASE/orders/DD-1")
grep -q '<div id="root">' <<<"$spa" || fail "SPA-маршрут /orders/… не отдаёт index.html"
panel=$(k "$BASE/panel/")
grep -qi 'id="root"' <<<"$panel" || fail "панель не открывается"
k -o /dev/null "$BASE/static/admin/css/base.css" || fail "статика Django не раздаётся"

step "Демо-каталог с фото"
python3 - "$BASE" <<'PY'
import json, ssl, sys, urllib.request

base = sys.argv[1]
ctx = ssl._create_unverified_context()
get = lambda url: urllib.request.urlopen(url, context=ctx, timeout=30)
products, url = [], f"{base}/api/v1/catalog/products/?page_size=100"
while url:
    page = json.load(get(url))
    products += page["results"]
    url = page["next"]
covers = [p["cover_url"] for p in products if p["cover_url"]]
assert len(products) >= 20, f"товаров {len(products)}"
assert len(covers) == len(products), f"без фото: {[p['slug'] for p in products if not p['cover_url']]}"
for cover in covers:
    with get(cover) as response:
        assert response.headers["Content-Type"].startswith("image/"), cover
        assert len(response.read()) > 5000, cover
detail = json.load(get(f"{base}/api/v1/catalog/products/{products[0]['slug']}/"))
assert detail["images"], "у товара нет галереи"
print(f"товаров {len(products)}, все с фото, фото отдаются")
PY

step "manage.py check --deploy"
"${COMPOSE[@]}" exec -T app python manage.py check --deploy --fail-level WARNING

step "Нагрузочный smoke оформления заказа"
python3 deploy/smoke_checkout.py "$BASE" --insecure --users 6 | tee "$OUT/smoke.log"
grep -q "SMOKE OK" "$OUT/smoke.log" || fail "smoke-тест"

step "Бэкап и восстановление"
before=$("${COMPOSE[@]}" exec -T db psql -U didi -d didi -tAc "select count(*) from orders_order")
./deploy.sh backup
db_dump=$(ls -t backups/db-*.dump | head -n 1)
media_tar=$(ls -t backups/media-*.tar.gz | head -n 1)
# Изменение после бэкапа должно исчезнуть после восстановления.
"${COMPOSE[@]}" exec -T db psql -U didi -d didi -c "update store_product set name = 'ПОСЛЕ БЭКАПА'" >/dev/null
./deploy.sh restore-yes "$db_dump" "$media_tar"
after=$("${COMPOSE[@]}" exec -T db psql -U didi -d didi -tAc "select count(*) from orders_order")
changed=$("${COMPOSE[@]}" exec -T db psql -U didi -d didi -tAc "select count(*) from store_product where name = 'ПОСЛЕ БЭКАПА'")
[ "$before" = "$after" ] && [ "$changed" = "0" ] || fail "восстановление: заказов $before → $after, изменённых товаров $changed"
k "$BASE/api/v1/health/" >/dev/null || fail "после восстановления сайт не отвечает"
echo "Бэкап $db_dump восстановлен: заказов $after, данные после бэкапа откатились."

step "Браузер: покупатель и администратор"
if ! python3 -c "import playwright" 2>/dev/null; then
  python3 -m pip install -q playwright
  python3 -m playwright install --with-deps chromium
fi
python3 deploy/e2e_browser.py "$BASE" "$OUT" | tee "$OUT/browser.log"
grep -q "BROWSER E2E OK" "$OUT/browser.log" || fail "браузерный сценарий"

printf '\n\033[1;32mE2E OK\033[0m\n'
