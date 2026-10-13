"""Планировщик периодических задач поверх django.tasks.

Планировщик только ставит задачи в очередь; выполняет их воркер того бэкенда,
что задан в TASKS. Поэтому смена бэкенда (Postgres → Redis/RQ) планировщик не трогает.
"""

import logging
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PeriodicTask:
    path: str
    every: int

    @property
    def task(self):
        return import_string(self.path)


def load_periodic_tasks() -> list[PeriodicTask]:
    tasks = []
    for entry in getattr(settings, "PERIODIC_TASKS", []):
        path, every = entry.get("task"), entry.get("every")
        if not path or not isinstance(every, int) or every < 1:
            raise ImproperlyConfigured(f"Некорректная запись PERIODIC_TASKS: {entry!r}")
        periodic = PeriodicTask(path=path, every=every)
        if not hasattr(periodic.task, "enqueue"):
            raise ImproperlyConfigured(f"{path} не является задачей (нет @task)")
        tasks.append(periodic)
    return tasks


def enqueue_due(tasks: list[PeriodicTask], now: float | None = None) -> list[str]:
    """Ставит в очередь задачи, у которых наступил новый интервал.

    Слот = номер интервала с эпохи. cache.add атомарен в db/redis-кэше, поэтому
    задача попадает в очередь один раз на слот даже при нескольких экземплярах
    планировщика и после его перезапуска.
    """
    now = time.time() if now is None else now
    enqueued = []
    for periodic in tasks:
        slot = int(now // periodic.every)
        lock_key = f"periodic:{periodic.path}:{slot}"
        if not cache.add(lock_key, 1, timeout=periodic.every * 2):
            continue
        periodic.task.enqueue()
        enqueued.append(periodic.path)
        logger.info("Периодическая задача поставлена в очередь: %s", periodic.path)
    return enqueued
