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
| Мобильное приложение | `/api/v1/catalog/categories/`, `/api/v1/catalog/products/?category=<slug>`, `/api/v1/catalog/products/<slug>/` | без аутентификации |
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
- Бизнес-правила — `store/services/catalog.py`, API — `store/api/`.

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

## Мобильное приложение (`mobile/`)

```bash
cd mobile
npm ci
npm run gen:api                                   # типы из ../openapi/schema.yml
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000 npx expo start
```

Адрес API — `EXPO_PUBLIC_API_URL` (эмулятор Android — `http://10.0.2.2:8000`, iOS-симулятор —
`http://localhost:8000`, телефон — IP компьютера; добавьте его в `ALLOWED_HOSTS`).
Проверка типов: `npm run typecheck`. Бизнес-логика — в `src/auth`, `src/cart` и `src/api`, экраны — в `app/`.
Каталог и корзина доступны без входа; вход и регистрация открываются модально, гостевая корзина
(AsyncStorage) после входа переносится в аккаунт.
Переход на Swift/Kotlin не затрагивает бэкенд: клиент для них генерируется из той же OpenAPI-схемы.

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
