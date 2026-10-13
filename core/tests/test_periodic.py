import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command

from core.periodic import PeriodicTask, enqueue_due, load_periodic_tasks
from core.tests import tasks_for_tests

TASK_PATH = "core.tests.tasks_for_tests.record_call"


@pytest.fixture(autouse=True)
def _reset():
    cache.clear()
    tasks_for_tests.CALLS.clear()


def test_enqueue_due_runs_once_per_slot():
    tasks = [PeriodicTask(path=TASK_PATH, every=60)]

    assert enqueue_due(tasks, now=120.0) == [TASK_PATH]
    # Тот же интервал (другой экземпляр планировщика или рестарт) — повторно не ставим.
    assert enqueue_due(tasks, now=150.0) == []
    # Следующий интервал.
    assert enqueue_due(tasks, now=180.0) == [TASK_PATH]

    # TASKS_BACKEND=immediate в тестах: задача выполнилась при постановке.
    assert tasks_for_tests.CALLS == ["called", "called"]


def test_load_periodic_tasks_validates_settings(settings):
    settings.PERIODIC_TASKS = [{"task": TASK_PATH, "every": 300}]
    assert load_periodic_tasks() == [PeriodicTask(path=TASK_PATH, every=300)]

    settings.PERIODIC_TASKS = [{"task": TASK_PATH, "every": 0}]
    with pytest.raises(ImproperlyConfigured):
        load_periodic_tasks()

    settings.PERIODIC_TASKS = [{"task": "core.tests.tasks_for_tests.not_a_task", "every": 60}]
    with pytest.raises(ImproperlyConfigured):
        load_periodic_tasks()


def test_run_scheduler_once(settings):
    settings.PERIODIC_TASKS = [{"task": TASK_PATH, "every": 60}]
    call_command("run_scheduler", "--once")
    assert tasks_for_tests.CALLS == ["called"]
