# DiDi-shop

https://avtorhanov.github.io/ThreadsAndTrends-Django-Emporium/

Интернет-магазин одного продавца: веб-витрина, мобильное приложение и панель администратора на общем API.
Роли — **Клиент** и **Администратор** (`is_staff`, единственный продавец). Деньги везде — целые копейки.

## Состав

| Каталог | Что это |
|---|---|
| корень | бэкенд: Django 5.2 LTS, PostgreSQL 16, DRF API `/api/v1/` (OpenAPI — `openapi/schema.yml`) |
| `accounts/`, `store/`, `orders/`, `payments/`, `content/` | пользователи, каталог и корзина, заказы, оплата ЮKassa, статьи и контакты; логика — `*/services/` |
| `web/` | веб-витрина: Django-шаблоны + htmx, серверный рендер, SEO |
| `mobile/` | приложение клиента: Expo (React Native), expo-router; APK — `.github/workflows/android.yml` |
| `admin-panel/` | панель администратора: React + Vite, адрес `/panel/` |
| `deploy/`, `compose.prod.yml`, `deploy.sh` | продакшен-стек (Caddy, gunicorn, worker, scheduler, Postgres, бэкапы) и e2e |
| `docs/design/lime-tech/` | дизайн «Лайм-тек»: `tokens.json` — единственный источник значений |

Аутентификация: приложение — JWT, витрина и панель — сессия Django + CSRF; `/api/v1/admin/…` принимает
только сессию администратора. Стандартная Django admin (`/admin/`) — резервный вход суперпользователя.

## Быстрый старт

```bash
docker compose up --build
```

- сайт — http://localhost:8000, API — `/api/v1/`, healthcheck — `/api/v1/health/`;
- OpenAPI — `/api/v1/schema/`, Swagger UI — `/api/v1/docs/` (в dev открыты всем, в prod — администратору);
- письма (коды сброса пароля) в dev — в логе воркера: `docker compose logs -f worker`;
- суперпользователь: `docker compose exec web python manage.py createsuperuser`.

Клиенты:

```bash
cd mobile && npm ci && EXPO_PUBLIC_API_URL=http://<IP компьютера>:8000 npx expo start
cd admin-panel && npm ci && npm run dev           # http://localhost:5173/panel/, прокси на :8000
```

## Разработка

```bash
ruff check . && ruff format --check .
pytest                                            # нужен Postgres (см. .env.example)
python manage.py spectacular --file openapi/schema.yml   # после изменения API; типы клиентов — npm run gen:api
python3 scripts/gen_tokens.py                     # после правки tokens.json
```

Настройки — `myshop/settings/{dev,test,prod}.py`, все параметры из окружения (`.env.example`).
Фоновые задачи — `django.tasks` (очередь в Postgres, `manage.py db_worker`), периодические —
`settings.PERIODIC_TASKS` + `manage.py run_scheduler`.

CI (`ci.yml`): ruff, актуальность миграций, OpenAPI-схемы и токенов, тесты на Postgres, `check --deploy`,
typecheck и сборка клиентов, Docker-образ, e2e прод-стека (`deploy/e2e.sh`).

## Продакшен

Пошагово для владельца — **[docs/LAUNCH.md](docs/LAUNCH.md)**: VPS → `.env` → `./deploy.sh` → ЮKassa.
Обновление — `git pull && ./deploy.sh`; подкоманды `status`, `logs`, `backup`, `restore`, `smoke`.
Без домена магазин работает на `https://<IP>.sslip.io`.

## Ветки

| Ветка | Назначение | Push запускает |
|---|---|---|
| `main` | то, что уходит на сервер; изменения только через PR | полный CI и e2e; теги `v*` — выпуск APK |
| `dev` | функционал: модели, миграции, сервисы, API, логика клиентов | полный CI и e2e, проверка сборки APK |
| `visual` | внешний вид: токены, `site.css`, шаблоны, шрифты, иконки, превью | только превью GitHub Pages |

- В `main` — только PR из `dev` или `visual` с зелёным CI, мёрж **merge-коммитом**.
- После мёржа `main` вливается обратно в `dev` и `visual` (`git merge origin/main`, без rebase и force-push).
- Фича, которой нужны и логика, и вид, делается целиком в `dev`; превью с `dev` — Actions → «Visual preview» → Run workflow.
- Служебные ветки: `gh-pages` (превью) и `ci-report-*` (журналы CI).
