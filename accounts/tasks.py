import logging
from datetime import timedelta

from django.utils import timezone
from django_tasks import task
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from .models import PasswordResetCode

logger = logging.getLogger(__name__)


@task()
def cleanup_auth_records() -> None:
    """Периодическая чистка (settings.PERIODIC_TASKS): истёкшие refresh-токены
    (вместе с записями чёрного списка) и старые коды сброса пароля."""
    now = timezone.now()
    tokens, _ = OutstandingToken.objects.filter(expires_at__lte=now).delete()
    codes, _ = PasswordResetCode.objects.filter(expires_at__lte=now - timedelta(days=1)).delete()
    logger.info("Чистка auth: удалено токенов %d, кодов сброса %d", tokens, codes)
