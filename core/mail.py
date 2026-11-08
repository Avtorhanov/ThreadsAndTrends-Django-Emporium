"""Отправка через несколько почтовых ящиков по очереди (настройки EMAIL_YANDEX_* и др.).

Если ящик не принял письмо (лимит, блокировка, сеть) — пробуем следующий. Адрес отправителя
подставляется от ящика: бесплатные сервисы отвергают письма с чужим From.
"""

import logging
from email.utils import formataddr, parseaddr
from smtplib import SMTPException

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)


class FailoverEmailBackend(BaseEmailBackend):
    def send_messages(self, messages) -> int:
        sent = 0
        for message in messages:
            try:
                sent += self._send(message)
            except (SMTPException, OSError):
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message) -> int:
        display_name = parseaddr(settings.DEFAULT_FROM_EMAIL)[0] or "DiDi-shop"
        error: Exception | None = None
        for relay in settings.EMAIL_RELAYS:
            backend = EmailBackend(
                host=relay["host"],
                port=relay["port"],
                username=relay["user"],
                password=relay["password"],
                use_ssl=True,
                use_tls=False,
                timeout=settings.EMAIL_TIMEOUT,
                fail_silently=False,
            )
            message.from_email = formataddr((display_name, relay["user"]))
            try:
                return backend.send_messages([message]) or 0
            except (SMTPException, OSError) as exc:
                error = exc
                logger.warning("Почтовый ящик %s не отправил письмо: %s", relay["name"], exc)
        if error is None:
            raise SMTPException("Не настроен ни один почтовый ящик")
        raise error
