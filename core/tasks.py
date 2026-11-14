import logging
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django_tasks import task

logger = logging.getLogger(__name__)

# Паузы перед повторами, секунды: сбой почты не должен терять письмо о заказе.
RETRY_DELAYS = (5 * 60, 30 * 60, 2 * 60 * 60)


@task()
def send_email(subject: str, body: str, recipients: list[str], attempt: int = 0) -> None:
    """Отправка письма из воркера: запрос API не ждёт SMTP и не падает при его сбое."""
    try:
        send_mail(subject=subject, message=body, from_email=None, recipient_list=recipients)
    except (SMTPException, OSError) as exc:
        if attempt >= len(RETRY_DELAYS):
            logger.error("Письмо «%s» не отправлено после всех попыток: %s", subject, exc)
            raise
        logger.warning("Письмо «%s» не отправлено, попытка %d: %s", subject, attempt + 1, exc)
        run_after = timezone.now() + timedelta(seconds=RETRY_DELAYS[attempt])
        send_email.using(run_after=run_after).enqueue(
            subject, body, recipients, attempt=attempt + 1
        )
        return
    logger.info("Письмо «%s» отправлено (%d получателей)", subject, len(recipients))


@task()
def prune_task_results() -> int:
    """Удаляет завершённые задачи старше TASK_RESULTS_KEEP_DAYS.

    Таблица очереди иначе только растёт: две периодические задачи в минуту — около 3 000 строк
    в сутки. Невыполненные (без finished_at) не трогаются.
    """
    # При другом бэкенде очереди (Redis) таблицы задач нет.
    if settings.TASKS["default"]["BACKEND"] != "django_tasks_db.DatabaseBackend":
        return 0
    from django_tasks_db.models import DBTaskResult

    cutoff = timezone.now() - timedelta(days=settings.TASK_RESULTS_KEEP_DAYS)
    deleted, _ = DBTaskResult.objects.filter(finished_at__lt=cutoff).delete()
    logger.info("Очередь задач: удалено завершённых записей — %d", deleted)
    return deleted
