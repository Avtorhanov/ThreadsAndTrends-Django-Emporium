# DiDi-shop

Маркетплейс DiDi-shop (монорепозиторий):

| Каталог | Что это |
|---|---|
| корень | бэкенд: Django 5.2 LTS, PostgreSQL, DRF API `/api/v1/` |
| `mobile/` | мобильное приложение клиента: Expo (React Native), expo-router |
| `admin-panel/` | панель администратора: React + Vite |
| `openapi/schema.yml` | OpenAPI-схема API; из неё генерируются типы обоих клиентов |

Роли: **Клиент** (мобильное приложение, JWT) и **Администратор** — единственный продавец
(`is_staff`, панель администратора, вход по сессии). Стандартная Django admin оставлена
только как резервный вход суперпользователя.

## Продакшен

Запуск на сервере — **[docs/LAUNCH.md](docs/LAUNCH.md)** (пошагово, для владельца): VPS → `.env` →
`./deploy.sh` → ЮKassa. Домен не обязателен: без него магазин работает на `https://<IP>.sslip.io`.

| Что | Как устроено |
|---|---|
| `./deploy.sh` | Docker, секреты, сборка, миграции, администратор, демо-каталог; он же — обновление (`git pull && ./deploy.sh`), `status`, `logs`, `backup`, `restore`, `smoke` |
| `compose.prod.yml` | `caddy` (HTTPS Let's Encrypt, веб-приложение `/app/`, панель `/panel/`, статика и фото; остальное — Django), `app` (gunicorn), `worker`, `scheduler`, `db` (Postgres 16), `backup` (ночной `pg_dump` + фото, 14 дней) |
| Веб-приложение | веб-версия `mobile/` (Expo web, `experiments.baseUrl=/app`) по адресу `https://<домен>/app/`; на iPhone ставится «На экран „Домой“» (PWA: `mobile/public/`). Корень `/` — Django: пока нет веб-витрины (сессия 8), ведёт в `/app/` (`SITE_ROOT_REDIRECT`), страницы на шаблонах (`/products/`, `/product/<slug>/`, …) остаются |
| Android | `.github/workflows/android.yml` → APK в GitHub Releases (`releases/latest/download/didi-shop.apk`) |
| Проверка | `bash deploy/e2e.sh` (CI, задание `e2e`): деплой одной командой с `DOMAIN=localhost`, HTTPS и заголовки, PWA, фото каталога, `check --deploy`, нагрузочный smoke оформления, бэкап → восстановление, сценарий покупателя и администратора в Chromium со скриншотами |
| Мониторинг | `GET /api/v1/health/` (БД + кэш), Sentry по `SENTRY_DSN`, логи — `./deploy.sh logs` |

## Быстрый старт (Docker)

```bash
docker compose up --build
```

- Сайт: http://localhost:8000
- API: http://localhost:8000/api/v1/ (healthcheck — `/api/v1/health/`)
- OpenAPI: http://localhost:8000/api/v1/schema/, Swagger UI — `/api/v1/docs/` (в dev открыты всем, в prod — только администратору)
- Резервная Django admin (только суперпользователь): http://localhost:8000/admin/
  (`docker compose exec web python manage.py createsuperuser` — спросит email и пароль)
- Письма (коды сброса пароля) в dev печатаются в лог воркера: `docker compose logs -f worker`

После обновления до сессии 2 пересоздайте локальную БД: миграции пересозданы с нуля
(`docker compose down -v && docker compose up --build`).

Сервисы: `db` (Postgres 16), `web` (миграции + демо-каталог + dev-сервер), `worker` (фоновые задачи),
`scheduler` (периодические задачи), `redis` (опционально, профиль `redis`).

## Локально без Docker

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env            # укажите доступ к своему Postgres
python manage.py migrate && python manage.py createcachetable
python manage.py loaddata fixtures/catalog.json
python manage.py runserver
```

## Пользователи и аутентификация

| Клиент | Аутентификация | Эндпоинты |
|---|---|---|
| Мобильное приложение | JWT: access 15 мин (в памяти), refresh 30 дней (SecureStore), ротация + чёрный список | `/api/v1/auth/…` |
| Панель администратора | сессия Django (httpOnly-cookie) + заголовок `X-CSRFToken` | `/api/v1/admin/…` |

- Вход по email (без учёта регистра); пароли проверяются `AUTH_PASSWORD_VALIDATORS`.
- Смена пароля — только со старым паролем; смена и сброс пароля завершают сессии на других устройствах.
- Сброс пароля: 6-значный код на email, действует 15 минут, 5 попыток, новый код — не чаще раза в минуту.
- Удаление аккаунта — мягкое (`deleted_at`): email и имя обезличиваются, токены отзываются, заказы
  сохраняются без персональных данных получателя. При незавершённых заказах удаление запрещено.
- Rate limit входа, регистрации и сброса пароля — по IP и по email (DRF throttling в общем кэше).
  За nginx задайте `NUM_PROXIES=1`, иначе IP берётся из соединения, а `X-Forwarded-For` игнорируется.
- Администратор (`is_staff`) создаётся суперпользователем в резервной Django admin; клиент
  стать администратором через API не может.

## Каталог

| Клиент | Эндпоинты | Доступ |
|---|---|---|
| Мобильное приложение и веб-витрина | `/api/v1/catalog/categories/` (из кэша), `/api/v1/catalog/products/?q=&category=&price_min=&price_max=&in_stock=&sort=`, `/api/v1/catalog/products/<slug>/` | без аутентификации |
| Панель администратора | `/api/v1/admin/catalog/{categories,products,variants,images}/…` | сессия + `IsAdmin` |

- Деньги — целые копейки (`price_kopecks`, `compare_at_kopecks` — «старая цена»), API отдаёт и
  принимает только копейки; рубли — форматирование в клиентах.
- Категории — дерево из двух уровней (`Category.parent`); товары лежат только в конечных категориях.
- Товар → варианты (`ProductVariant`: размер, артикул, остаток). Товар без размеров — один вариант
  «Без размера». «В наличии» вычисляется из остатков, точные остатки клиенту не отдаются.
- Галерея — до 10 фото (JPEG/PNG/WebP, до 5 МБ), первое — обложка. Хранение — `STORAGES["default"]`
  (локально `MEDIA_ROOT`; S3-совместимое хранилище — сессия 7).
- URL — по slug (транслит названия, при переименовании не меняется).
- Удаление товара мягкое (`deleted_at`): `Product.objects` скрывает удалённые, `Product.all_objects` —
  все; история заказов сохраняется (`OrderItem.product` — `PROTECT`). Категорию с товарами
  (в т.ч. удалёнными) удалить нельзя — только скрыть.
- Поиск — полнотекстовый Postgres (русская морфология, по началу слов, название важнее описания,
  GIN-индекс `product_search_idx`); с поиском показываются только товары в наличии. Фильтры: категория
  с подкатегориями, цена в копейках, наличие; сортировка `new`, `price_asc`, `price_desc`, `relevance`.
  Логика — `store/services/storefront.py`.
- Бизнес-правила — `store/services/catalog.py`, API — `store/api/`.
- Демо-каталог: `python manage.py seed_demo` — товары из `fixtures/catalog.json` и фото
  `fixtures/demo_images/` (источники и лицензии — `CREDITS.md`, обновление — `scripts/fetch_demo_images.py`).

## Корзина

| Кто | Где хранится | Эндпоинты |
|---|---|---|
| Клиент (JWT) | в БД: `Cart` (одна на пользователя) → `CartItem` (вариант товара, количество) | `GET /api/v1/cart/`, `POST items/`, `PATCH`/`DELETE items/<id>/`, `POST ack-prices/` |
| Гость | на устройстве (`{variant_id, quantity, seen_price_kopecks}`) | `POST /api/v1/cart/quote/` — расчёт без записи, без входа; после входа или регистрации — `POST /api/v1/cart/merge/` |

- Цена в корзине не хранится: сумма = текущая цена × количество. Оформление заказа (сессия 5)
  использует тот же расчёт (`store.services.cart.get_summary`), поэтому показанная сумма совпадает с суммой заказа.
- Позиция получает статус: `ok`, `unavailable` (товар снят, скрыт или удалён), `out_of_stock`,
  `exceeds_stock` (в корзине больше доступного). В `total_kopecks` входят только позиции `ok`;
  `can_checkout` — корзина не пуста и все позиции `ok`. Чтение корзину не меняет.
- Количество: от 1 до `min(остаток, CART_MAX_QUANTITY)` (по умолчанию 10); не больше `CART_MAX_ITEMS`
  позиций (50). Остатки не резервируются — это делает оформление заказа.
- «Цена изменилась»: `seen_price_kopecks` — цена, которую покупатель видел последней (в расчётах не
  участвует); предупреждение снимает `POST ack-prices/` («Понятно» в приложении).
- При слиянии количества складываются и ограничиваются доступным; недоступные позиции пропускаются,
  об этом сообщает `notices`. Чужая позиция → 404.
- Логика — `store/services/cart.py`, API — `store/api/cart_views.py`. Корзина есть только в мобильном
  приложении: страницы корзины и оформления легаси-сайта удалены.

## Заказы

| Кто | Эндпоинты |
|---|---|
| Клиент (JWT) | `GET /api/v1/orders/checkout/` — экран оформления; `POST /api/v1/orders/` (заголовок `Idempotency-Key`) — оформить; `GET /api/v1/orders/`, `GET <номер>/`, `POST <номер>/cancel/` |
| Администратор (сессия) | `GET /api/v1/admin/orders/` (фильтры `status`, `unfinished`, `payment_method`, `delivery_method`, `created_from/to`, поиск), `GET <id>/`, `POST <id>/transition/` |

- Оформление — вся корзина, только после входа. Сумма считается тем же `get_summary`, что и в корзине;
  под `select_for_update` корзины и вариантов позиции перепроверяются, остатки списываются, корзина очищается.
  `expected_total_kopecks` — итог, который видел покупатель: если сумма изменилась, заказ не создаётся (400).
- Повтор запроса с тем же `Idempotency-Key` возвращает уже созданный заказ (200), второго списания нет.
- Номер — `DD-100001…` из последовательности Postgres `orders_order_number_seq`.
- Позиция заказа ссылается на вариант (PROTECT) и хранит снимок: название, размер, артикул, цену.
- Статусы (`orders/services/status.py`):

  ```
  онлайн-оплата:  awaiting_payment → paid ─┐
  при получении:  confirmed ───────────────┴→ assembled → shipped (курьер) | ready_for_pickup (самовывоз) → delivered
  отмена:         из любого незавершённого статуса, кроме shipped
  ```

  Клиент отменяет заказ до отправки (`awaiting_payment`, `confirmed`, `paid`, `assembled`).
  Администратор собирает, отправляет, выдаёт и отменяет; `paid` ставит только платёжная система
  (`mark_paid`). Отмена возвращает остатки и шлёт сигнал `orders.signals.order_cancelled`
  (`was_paid=True` — возврат денег, см. «Оплата»). Каждая смена статуса — запись в истории и письмо клиенту.
- Доставка: курьер `DELIVERY_COURIER_KOPECKS` (500 ₽), бесплатно от `DELIVERY_FREE_FROM_KOPECKS`
  (10 000 ₽); самовывоз бесплатно, предлагается, если задан `PICKUP_ADDRESS`. Онлайн-оплата предлагается
  при `ORDERS_ONLINE_PAYMENT_ENABLED=True` (нужны ключи ЮKassa, см. «Оплата»).
- Удаление аккаунта запрещено при незавершённых заказах; после удаления данные получателя в заказах стираются.

## Оплата (ЮKassa)

| Кто | Эндпоинты |
|---|---|
| Клиент (JWT) | `POST /api/v1/orders/<номер>/pay/` → `confirmation_url`; `POST /api/v1/orders/<номер>/pay/refresh/` — сверка после возврата из браузера |
| ЮKassa | `POST /api/v1/payments/webhook/yookassa/` — уведомления (без аутентификации, проверка IP) |
| Администратор (сессия) | `POST /api/v1/admin/orders/<id>/payment-sync/` — сверить оплату, `POST <id>/refund/` — повторить возврат |

- Поток: заказ «Ожидает оплаты» → приложение получает ссылку на страницу ЮKassa (карта, СБП, SberPay, T-Pay)
  и открывает её во встроенном браузере → покупатель возвращается по deep link `didishop://orders/<номер>` →
  сервер сверяет платёж и переводит заказ в «Оплачен» (`mark_paid`). Оплата одностадийная (`capture=true`).
- **Статус берётся только из API ЮKassa.** Уведомление — лишь повод перезапросить платёж по API; его тело,
  ответ приложения и параметры страницы возврата не доверяются. Webhook принимается только с адресов ЮKassa
  (`YOOKASSA_WEBHOOK_IPS`; за nginx — `NUM_PROXIES=1`). Сумма и валюта сверяются с `Order.total_kopecks`.
- Повторы безопасны: `Idempotence-Key` у каждого платежа и возврата (сбой сети → повтор с тем же ключом),
  одна незавершённая попытка оплаты на заказ (повторное «Оплатить» возвращает ту же ссылку), повторный webhook
  ничего не меняет.
- Деньги, которые не могут оплатить заказ, возвращаются автоматически: оплата после отмены заказа,
  повторная оплата, несовпавшая сумма. Отмена оплаченного заказа (клиентом до отправки или администратором)
  оформляет полный возврат по сигналу `order_cancelled`. Возврат выполняется фоновой задачей; отказ
  провайдера виден в панели («Повторить возврат»). О возврате клиенту уходит письмо.
- Неоплаченный онлайн-заказ отменяется через `ORDERS_UNPAID_TIMEOUT_MINUTES` (30 мин), остатки возвращаются.
  Перед отменой платёж сверяется; если ЮKassa недоступна — отмена откладывается до следующего запуска.
- Периодические задачи: `payments.tasks.sync_pending` (зависшие платежи и возвраты, раз в минуту),
  `payments.tasks.cancel_unpaid_orders` (автоотмена, раз в минуту).
- Чеки 54-ФЗ — «Чеки от ЮKassa»: позиции заказа + доставка, email покупателя. Система налогообложения,
  ставка НДС и признак расчёта — настройки (`PAYMENTS_TAX_SYSTEM_CODE`, `PAYMENTS_VAT_CODE`,
  `PAYMENTS_RECEIPT_PAYMENT_MODE`), по умолчанию «УСН доходы, без НДС, полный расчёт».
  **Сверьте их с бухгалтером до запуска.** Самозанятым — `PAYMENTS_RECEIPTS_ENABLED=False` (чек через «Мой налог»).
  Оплату при получении фискализирует касса курьера/пункта выдачи — приложение её не касается.

### Подключение ЮKassa

1. Зарегистрируйте магазин в ЮKassa и создайте **тестовый магазин** в личном кабинете — у него свои
   `shopId` и секретный ключ, деньги не списываются (тестовые карты — в документации ЮKassa).
2. В `.env` (не в репозиторий): `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `ORDERS_ONLINE_PAYMENT_ENABLED=True`.
   Без ключей при включённой онлайн-оплате Django не запустится (system check `payments.E001`).
3. Адрес возврата в Expo Go начинается с `exp://` — в dev он разрешён по умолчанию
   (`PAYMENTS_RETURN_URL_PREFIXES=didishop://,exp://`); в prod — только `didishop://` (сборка приложения).
4. Локально (без публичного адреса) оплата подтверждается сверкой: приложение вызывает `pay/refresh/` после
   возврата из браузера, а `sync_pending` раз в минуту проверяет зависшие платежи. Уведомления включаются
   после деплоя ([docs/LAUNCH.md](docs/LAUNCH.md), шаг 8): в кабинете ЮKassa → Интеграция → HTTP-уведомления — адрес
   `https://<домен>/api/v1/payments/webhook/yookassa/`, события `payment.succeeded`, `payment.canceled`,
   `refund.succeeded`.
5. Боевые ключи — только после проверки полного цикла на тестовом магазине.

## Мобильное приложение (`mobile/`)

```bash
cd mobile
npm ci
npm run gen:api                                   # типы из ../openapi/schema.yml
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000 npx expo start
```

Адрес API — `EXPO_PUBLIC_API_URL` (эмулятор Android — `http://10.0.2.2:8000`, iOS-симулятор —
`http://localhost:8000`, телефон — IP компьютера; добавьте его в `ALLOWED_HOSTS`).
Проверка типов: `npm run typecheck`. Бизнес-логика — в `src/auth`, `src/cart`, `src/orders` и `src/api`,
экраны — в `app/`. Каталог и корзина доступны без входа; вход и регистрация открываются модально, гостевая
корзина (AsyncStorage) после входа переносится в аккаунт. Оформление, «Мои заказы» (вход из профиля)
и отмена заказа — только после входа. Оплата — кнопка «Оплатить» на экране заказа (`src/orders/payment.ts`):
страница ЮKassa во встроенном браузере (`expo-web-browser`), возврат по deep link, затем сверка на сервере.
Переход на Swift/Kotlin не затрагивает бэкенд: клиент для них генерируется из той же OpenAPI-схемы.

Навигация — плавающие вкладки «Каталог», «Поиск», «Корзина», «Профиль» (`app/(app)/(tabs)`, панель —
`src/components/TabBar.tsx`); карточка товара открывается листом снизу поверх вкладок. Каталог: стеклянная
шапка со сворачиванием при прокрутке, категории — сегменты, лента 2–4 колонки. «Поиск»: поле, категории,
сортировка, цена «от/до» в рублях (в API уходят копейки, `parseRubles` без float), «В наличии».
Профиль гостя — вход и регистрация; тема (как в системе / светлая / тёмная) — в профиле и кнопкой в шапке.

Дизайн «Лайм-тек» (`docs/design/lime-tech/`): значения — только из `tokens.json`. После правки токенов —
`python3 scripts/gen_tokens.py` (пишет `mobile/src/theme/tokens.ts` и `tokens.css` для веб-витрины; CI
проверяет актуальность и контраст текста ≥ 4.5:1). Тема — `src/theme/ThemeProvider.tsx` (`useTheme`,
`makeStyles`), шрифты Unbounded и Manrope — `@expo-google-fonts/*`, анимации — Reanimated
(«Уменьшить движение» учитывается), общие компоненты — `src/components/ui.tsx`.

Веб-версия: `npx expo export --platform web` — собирается в образ Caddy (`deploy/edge.Dockerfile`),
работает по адресу `/app/` (`experiments.baseUrl`), API — тот же домен. Платформенные файлы `*.web.ts(x)`: хранение токена,
подтверждения (`window.confirm`), оплата в той же вкладке, подсказка установки на iPhone/Android.
APK: `.github/workflows/android.yml` (`expo prebuild` + Gradle, адрес магазина — `API_URL`).
Иконки — `python3 scripts/make_icons.py` (после `npm ci` в `mobile/`: шрифт берётся из пакета).

## Панель администратора (`admin-panel/`)

```bash
cd admin-panel
npm ci
npm run dev                                       # http://localhost:5173/panel/
```

Vite проксирует `/api` и `/media` на `http://localhost:8000` (`VITE_BACKEND_URL`), поэтому cookie сессии и CSRF
работают как на одном домене. В продакшене панель раздаётся nginx по `/panel/` с того же домена,
что и API (сессия 7). `npm run build` → `admin-panel/dist/`.

## OpenAPI и типы клиентов

После изменения API обновите схему и закоммитьте её (CI проверяет актуальность):

```bash
python manage.py spectacular --file openapi/schema.yml
```

Типы TypeScript (`src/api/schema.d.ts`) генерируются в каждом клиенте командой `npm run gen:api`
(автоматически перед `typecheck` и `build`) и в git не хранятся.

## Настройки

| Модуль | Назначение |
|---|---|
| `myshop.settings.dev` | разработка (по умолчанию для `manage.py`) |
| `myshop.settings.test` | тесты (по умолчанию для `pytest`) |
| `myshop.settings.prod` | продакшен (по умолчанию для WSGI/ASGI и Docker-образа) |

Инфраструктура переключается переменными окружения, без правок кода:

| Переменная | Значения | По умолчанию |
|---|---|---|
| `CACHE_URL` | `db://django_cache`, `redis://host:6379/1`, `locmem://`, `dummy://` | `db://django_cache` |
| `TASKS_BACKEND` | `database`, `immediate`, `dummy` или полный путь к классу бэкенда | `database` |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_*` | SMTP-провайдер писем | dev — консоль, prod — SMTP |
| `NUM_PROXIES` | число доверенных прокси (за nginx — `1`) | `0` |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | время жизни токенов | `15`, `30` |
| `THROTTLE_*` | лимиты попыток (см. `.env.example`) | см. `settings/base.py` |
| `CART_MAX_QUANTITY`, `CART_MAX_ITEMS` | лимиты корзины: единиц одного товара (не больше остатка) и позиций | `10`, `50` |
| `DELIVERY_COURIER_KOPECKS`, `DELIVERY_FREE_FROM_KOPECKS` | стоимость курьера и порог бесплатной доставки, коп. | `50000`, `1000000` |
| `PICKUP_ADDRESS` | адрес пункта самовывоза (пусто — без самовывоза) | пусто |
| `ORDERS_ONLINE_PAYMENT_ENABLED` | предлагать онлайн-оплату (нужны ключи ЮKassa) | `False` |
| `ORDERS_UNPAID_TIMEOUT_MINUTES` | автоотмена неоплаченного онлайн-заказа, мин | `30` |
| `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` | ключи магазина ЮKassa | пусто |
| `YOOKASSA_WEBHOOK_IPS` | адреса уведомлений ЮKassa (через запятую, CIDR) | список ЮKassa |
| `PAYMENTS_RETURN_URL_PREFIXES` | разрешённые адреса возврата в приложение | `didishop://` |
| `PAYMENTS_RECEIPTS_ENABLED` | передавать чеки 54-ФЗ | `True` |
| `PAYMENTS_TAX_SYSTEM_CODE`, `PAYMENTS_VAT_CODE` | система налогообложения и ставка НДС (коды ЮKassa) | `2` (УСН доходы), `1` (без НДС) |
| `PAYMENTS_RECEIPT_PAYMENT_MODE` | признак способа расчёта в чеке | `full_payment` |

## Фоновые и периодические задачи

Задачи пишутся на стандартном API `django.tasks` (бэкпорт `django-tasks`; при переходе на Django 6.x
меняется только импорт `django_tasks` → `django.tasks`):

```python
from django_tasks import task


@task()
def cancel_unpaid_orders(): ...


cancel_unpaid_orders.enqueue()
```

- Очередь по умолчанию — таблица в Postgres (`django-tasks-db`), воркер: `python manage.py db_worker`.
- Переход на Redis: `TASKS_BACKEND=django_tasks_rq.RQBackend` + пакет `django-tasks-rq`; код задач не меняется.
- Периодические задачи регистрируются в `settings.PERIODIC_TASKS` (`{"task": "app.tasks.func", "every": 300}`),
  в очередь их ставит `python manage.py run_scheduler`. Повторная постановка в одном интервале исключена
  блокировкой в общем кэше, поэтому несколько экземпляров планировщика безопасны.

## Качество

```bash
ruff check . && ruff format --check .
pytest
```

CI (GitHub Actions): ruff, проверка миграций, валидация и актуальность OpenAPI-схемы, тесты на Postgres,
`check --deploy` для prod-настроек, typecheck мобильного приложения и панели, сборка панели,
сборка Docker-образа и подъём dev-стека.
