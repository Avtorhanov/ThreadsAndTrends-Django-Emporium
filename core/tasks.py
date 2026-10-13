import logging

from django.core.mail import send_mail
from django_tasks import task

logger = logging.getLogger(__name__)


@task()
def send_email(subject: str, body: str, recipients: list[str]) -> None:
    """Отправка письма из воркера: запрос API не ждёт SMTP и не падает при его сбое."""
    send_mail(subject=subject, message=body, from_email=None, recipient_list=recipients)
    logger.info("Письмо «%s» отправлено (%d получателей)", subject, len(recipients))
