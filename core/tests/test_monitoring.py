import os
import time
from collections import namedtuple
from unittest import mock

import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from core import monitoring

pytestmark = pytest.mark.django_db

Usage = namedtuple("Usage", "total used free")


@pytest.fixture(autouse=True)
def isolated(settings, tmp_path):
    cache.clear()
    settings.MEDIA_ROOT = tmp_path


def test_no_task_activity_is_a_failure(settings):
    settings.TASKS = {"default": {"BACKEND": "django_tasks_db.DatabaseBackend"}}
    assert monitoring._task_checks() == {"scheduler": False, "worker": False}


def test_old_backup_is_a_failure(settings, tmp_path):
    settings.BACKUP_DIR = str(tmp_path)
    marker = tmp_path / ".ok-local"
    marker.touch()
    assert monitoring.service_checks()["backup_local"] is True
    old = time.time() - 27 * 60 * 60
    os.utime(marker, (old, old))
    assert monitoring.service_checks()["backup_local"] is False


def test_remote_backup_checked_only_when_configured(settings, tmp_path):
    settings.BACKUP_DIR = str(tmp_path)
    assert "backup_remote" not in monitoring.service_checks()
    settings.BACKUP_GDRIVE_TOKEN = "{}"
    assert "backup_remote" in monitoring.service_checks()


def test_remote_backup_that_never_succeeded_is_a_failure(settings, tmp_path):
    # Локальные копии обновляют время папки — по нему срок выгрузки считать нельзя.
    settings.BACKUP_DIR = str(tmp_path)
    settings.BACKUP_GDRIVE_TOKEN = "{}"
    first_run = tmp_path / ".first-run"
    first_run.touch()
    (tmp_path / ".ok-local").touch()
    assert monitoring.service_checks()["backup_remote"] is True
    old = time.time() - 27 * 60 * 60
    os.utime(first_run, (old, old))
    checks = monitoring.service_checks()
    assert checks["backup_remote"] is False
    assert checks["backup_local"] is True


def test_alert_is_retried_when_mail_fails(settings):
    settings.ALERT_EMAIL = "owner@example.com"
    with mock.patch("core.monitoring.shutil.disk_usage", return_value=Usage(100, 95, 5)):
        with mock.patch("core.monitoring.send_mail", side_effect=OSError("smtp")):
            with pytest.raises(OSError):
                monitoring.check_and_alert()
        assert monitoring.check_and_alert() == ["disk"]
    assert len(mail.outbox) == 1


def test_full_disk_alerts_once(settings):
    settings.ALERT_EMAIL = "owner@example.com"
    with mock.patch("core.monitoring.shutil.disk_usage", return_value=Usage(100, 95, 5)):
        assert monitoring.check_and_alert() == ["disk"]
        assert monitoring.check_and_alert() == []
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["owner@example.com"]


def test_full_health_reports_failure(client):
    with mock.patch("core.monitoring.shutil.disk_usage", return_value=Usage(100, 95, 5)):
        response = client.get(reverse("v1:health-full"))
    assert response.status_code == 503
    assert response.json()["checks"]["disk"] is False
    assert client.get(reverse("v1:health")).status_code == 200
