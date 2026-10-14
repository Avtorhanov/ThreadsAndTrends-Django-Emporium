"""Чтение конфигурации из переменных окружения.

Вся инфраструктура (БД, кэш, очередь задач) выбирается переменными окружения,
чтобы переключение бэкенда не требовало правок кода.
"""

import os
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ImproperlyConfigured

TRUE_VALUES = {"1", "true", "yes", "on"}


def env_str(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ImproperlyConfigured(f"Переменная окружения {name} не задана")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} должна быть целым числом") from exc


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} должна быть числом") from exc


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def database_from_env() -> dict:
    """PostgreSQL из DB_*; SQLite намеренно не поддерживается (select_for_update, FTS)."""
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("DB_NAME"),
        "USER": env_str("DB_USER"),
        "PASSWORD": env_str("DB_PASSWORD"),
        "HOST": env_str("DB_HOST", "localhost"),
        "PORT": env_str("DB_PORT", "5432"),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"connect_timeout": env_int("DB_CONNECT_TIMEOUT", 5)},
    }


def cache_from_url(url: str) -> dict:
    """CACHE_URL → настройки CACHES['default'].

    db://django_cache          — таблица кэша в основной БД (по умолчанию)
    redis://host:6379/1        — Redis (rediss:// для TLS)
    locmem://                  — память процесса (тесты, локальная отладка)
    dummy://                   — кэш отключён
    Параметр ?timeout=N задаёт TTL по умолчанию в секундах.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme
    query = parse_qs(parsed.query)
    config: dict = {"KEY_PREFIX": "didi"}

    if "timeout" in query:
        config["TIMEOUT"] = int(query["timeout"][0])

    if scheme == "db":
        table = parsed.netloc or parsed.path.lstrip("/") or "django_cache"
        config.update(BACKEND="django.core.cache.backends.db.DatabaseCache", LOCATION=table)
    elif scheme in ("redis", "rediss"):
        # Экранирование в пароле не трогаем: redis-py сам раскодирует URL.
        location = parsed._replace(query="").geturl()
        config.update(BACKEND="django.core.cache.backends.redis.RedisCache", LOCATION=location)
    elif scheme == "locmem":
        config.update(
            BACKEND="django.core.cache.backends.locmem.LocMemCache",
            LOCATION=parsed.netloc or "didi",
        )
    elif scheme == "dummy":
        config.update(BACKEND="django.core.cache.backends.dummy.DummyCache")
    else:
        raise ImproperlyConfigured(f"Неподдерживаемая схема CACHE_URL: {scheme!r}")
    return config


TASK_BACKENDS = {
    "database": "django_tasks_db.DatabaseBackend",
    "immediate": "django_tasks.backends.immediate.ImmediateBackend",
    "dummy": "django_tasks.backends.dummy.DummyBackend",
}


def tasks_from_env(name: str = "TASKS_BACKEND", default: str = "database") -> dict:
    """TASKS_BACKEND → настройки TASKS['default'].

    Короткие имена: database | immediate | dummy. Любой другой бэкенд
    (например, django_tasks_rq.RQBackend для Redis) задаётся полным путём к классу.
    """
    value = env_str(name, default)
    backend = TASK_BACKENDS.get(value, value)
    if "." not in backend:
        raise ImproperlyConfigured(f"Неизвестный {name}: {value!r}")
    return {"BACKEND": backend, "QUEUES": env_list("TASKS_QUEUES", "default")}
