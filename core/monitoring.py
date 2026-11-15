"""Проверка служб магазина и оповещение владельца на email.

Проверку запускает планировщик (run_scheduler), письмо уходит напрямую, мимо очереди: очередь
может стоять как раз из-за сбоя. Если сервер или планировщик упал целиком, письма не будет —
для этого внешняя проверка /api/v1/health/full/ (docs/LAUNCH.md, «Мониторинг»).
"""

import logging
import shutil
import time
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)

TASK_ACTIVITY_WINDOW = timedelta(minutes=5)
ALERT_REPEAT_SECONDS = 6 * 60 * 60
LABELS = {
    "worker": "Фоновые задачи не выполняются (worker): письма и автоотмена заказов стоят.",
    "scheduler": "Планировщик не ставит задачи (scheduler): автоотмена заказов стоит.",
    "backup_local": "Бэкап на сервере давно не обновлялся.",
    "backup_remote": "Копия в Google Диск давно не обновлялась.",
    "disk": "Диск сервера почти заполнен.",
}


def _task_checks() -> dict[str, bool]:
    # При другом бэкенде очереди (Redis) таблицы задач нет — проверять нечем.
    if settings.TASKS["default"]["BACKEND"] != "django_tasks_db.DatabaseBackend":
        return {}
    from django_tasks_db.models import DBTaskResult

    since = timezone.now() - TASK_ACTIVITY_WINDOW
    try:
        return {
            # Периодические задачи идут каждую минуту, поэтому тишина за 5 минут — сбой.
            "scheduler": DBTaskResult.objects.filter(enqueued_at__gte=since).exists(),
            "worker": DBTaskResult.objects.filter(finished_at__gte=since).exists(),
        }
    except Exception:
        logger.exception("Мониторинг: таблица задач недоступна")
        return {"scheduler": False, "worker": False}


def _backup_fresh(marker: str) -> bool:
    directory = Path(settings.BACKUP_DIR)
    # Удачной копии ещё не было — срок считаем от первой попытки (.first-run ставит backup.sh),
    # а до неё — от создания папки при деплое. Время самой папки после первой попытки не годится:
    # его обновляет каждый локальный бэкап, и ни разу не удавшаяся выгрузка выглядела бы свежей.
    candidates = (directory / marker, directory / ".first-run")
    path = next((p for p in candidates if p.exists()), directory)
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return False
    return age < settings.BACKUP_MAX_AGE_HOURS * 60 * 60


def _disk_ok() -> bool:
    usage = shutil.disk_usage(settings.MEDIA_ROOT)
    return usage.used / usage.total * 100 < settings.DISK_MAX_PERCENT


def service_checks() -> dict[str, bool]:
    checks = {**_task_checks(), "disk": _disk_ok()}
    if settings.BACKUP_DIR:
        checks["backup_local"] = _backup_fresh(".ok-local")
        if settings.BACKUP_GDRIVE_TOKEN:
            checks["backup_remote"] = _backup_fresh(".ok-remote")
    return checks


def _alert_key(name: str) -> str:
    return f"monitoring:alert:{name}"


def _should_alert(name: str) -> bool:
    try:
        return cache.get(_alert_key(name)) is None
    except Exception:  # кэш — в той же базе: при её сбое лучше лишнее письмо, чем никакого
        logger.exception("Мониторинг: кэш недоступен")
        return True


def _mark_alerted(names: list[str]) -> None:
    try:
        cache.set_many({_alert_key(name): 1 for name in names}, timeout=ALERT_REPEAT_SECONDS)
    except Exception:
        logger.exception("Мониторинг: кэш недоступен")


def check_and_alert() -> list[str]:
    """Письмо о новых сбоях (об одном и том же — не чаще раза в 6 часов).

    Пауза ставится после отправки: если письмо не ушло (сбой почты), следующая проверка
    через 10 минут попробует снова.
    """
    failed = [name for name, ok in service_checks().items() if not ok and _should_alert(name)]
    if not failed:
        return []
    body = "\n".join(LABELS[name] for name in failed)
    logger.error("Мониторинг: %s", body)
    if settings.ALERT_EMAIL:
        send_mail(
            subject="DiDi-shop: сбой на сервере",
            message=f"{body}\n\nПодробности: ./deploy.sh status и ./deploy.sh logs на сервере.",
            from_email=None,
            recipient_list=[settings.ALERT_EMAIL],
        )
    _mark_alerted(failed)
    return failed
