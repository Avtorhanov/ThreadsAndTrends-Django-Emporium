import pytest
from django.core.exceptions import ImproperlyConfigured

from core.env import cache_from_url, env_bool, env_int, env_list, tasks_from_env


@pytest.mark.parametrize(
    ("url", "backend", "location"),
    [
        ("db://django_cache", "django.core.cache.backends.db.DatabaseCache", "django_cache"),
        (
            "redis://redis:6379/1",
            "django.core.cache.backends.redis.RedisCache",
            "redis://redis:6379/1",
        ),
        (
            "rediss://:p%40ss@host:6380/0",
            "django.core.cache.backends.redis.RedisCache",
            "rediss://:p%40ss@host:6380/0",
        ),
        ("locmem://", "django.core.cache.backends.locmem.LocMemCache", "didi"),
    ],
)
def test_cache_from_url(url, backend, location):
    config = cache_from_url(url)
    assert config["BACKEND"] == backend
    assert config["LOCATION"] == location


def test_cache_from_url_timeout_and_dummy():
    assert cache_from_url("db://t?timeout=60")["TIMEOUT"] == 60
    assert cache_from_url("dummy://")["BACKEND"].endswith("DummyCache")


def test_cache_from_url_rejects_unknown_scheme():
    with pytest.raises(ImproperlyConfigured):
        cache_from_url("memcached://localhost")


def test_tasks_from_env_aliases_and_dotted_path(monkeypatch):
    monkeypatch.setenv("TASKS_BACKEND", "database")
    assert tasks_from_env()["BACKEND"] == "django_tasks_db.DatabaseBackend"

    monkeypatch.setenv("TASKS_BACKEND", "django_tasks_rq.RQBackend")
    assert tasks_from_env()["BACKEND"] == "django_tasks_rq.RQBackend"

    monkeypatch.setenv("TASKS_BACKEND", "celery")
    with pytest.raises(ImproperlyConfigured):
        tasks_from_env()


def test_env_helpers(monkeypatch):
    monkeypatch.setenv("FLAG", "Yes")
    monkeypatch.setenv("NUM", "42")
    monkeypatch.setenv("HOSTS", " a.ru, ,b.ru ")
    assert env_bool("FLAG") is True
    assert env_bool("MISSING", default=True) is True
    assert env_int("NUM", 0) == 42
    assert env_list("HOSTS") == ["a.ru", "b.ru"]

    monkeypatch.setenv("NUM", "abc")
    with pytest.raises(ImproperlyConfigured):
        env_int("NUM", 0)
