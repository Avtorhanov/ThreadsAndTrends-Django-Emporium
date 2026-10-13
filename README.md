# DiDi-shop

Бэкенд маркетплейса DiDi-shop: Django 5.2 LTS, PostgreSQL, DRF API для мобильного приложения.
Роли: Клиент и Администратор (единственный продавец, работает через Django admin).

## Быстрый старт (Docker)

```bash
docker compose up --build
```

- Сайт: http://localhost:8000
- API: http://localhost:8000/api/v1/ (healthcheck — `/api/v1/health/`)
- OpenAPI: http://localhost:8000/api/v1/schema/, Swagger UI — `/api/v1/docs/` (в dev открыты всем, в prod — только администратору)
- Админка: http://localhost:8000/admin/ (`docker compose exec web python manage.py createsuperuser`)

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

CI (GitHub Actions): ruff, проверка миграций, валидация OpenAPI-схемы, тесты на Postgres,
`check --deploy` для prod-настроек, сборка Docker-образа.
