from datetime import timedelta

import pytest
from django.utils import timezone
from django_tasks_db.models import DBTaskResult

from core.tasks import prune_task_results
from core.tests import tasks_for_tests

pytestmark = pytest.mark.django_db
DB_BACKEND = {"default": {"BACKEND": "django_tasks_db.DatabaseBackend"}}


def test_prune_skips_other_backends():
    assert prune_task_results.func() == 0


def test_prune_removes_only_old_finished_results(settings):
    settings.TASKS = DB_BACKEND
    settings.TASK_RESULTS_KEEP_DAYS = 7
    for _ in range(3):
        tasks_for_tests.record_call.enqueue()
    old, fresh, pending = DBTaskResult.objects.order_by("enqueued_at")
    now = timezone.now()
    DBTaskResult.objects.filter(pk=old.pk).update(finished_at=now - timedelta(days=8))
    DBTaskResult.objects.filter(pk=fresh.pk).update(finished_at=now - timedelta(days=1))

    assert prune_task_results.func() == 1
    assert set(DBTaskResult.objects.values_list("pk", flat=True)) == {fresh.pk, pending.pk}
