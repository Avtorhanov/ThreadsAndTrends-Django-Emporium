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

# Домены получателей по сервисам: письмо внутри одного сервиса реже попадает в спам.
RELAY_DOMAINS = {
    "Яндекс": {"yandex.ru", "ya.ru", "yandex.com", "yandex.by", "yandex.kz", "narod.ru"},
    "Mail.ru": {"mail.ru", "inbox.ru", "list.ru", "bk.ru", "internet.ru"},
    "Gmail": {"gmail.com", "googlemail.com"},
}


def relays_for(recipients: list[str]) -> list[dict]:
    """Ящики в порядке попыток: сначала сервис получателя, затем остальные как настроены."""
    domain = recipients[0].rpartition("@")[2].lower() if recipients else ""
    # sorted устойчив: порядок остальных ящиков сохраняется.
    return sorted(
        settings.EMAIL_RELAYS, key=lambda relay: domain not in RELAY_DOMAINS[relay["name"]]
    )


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
        for relay in relays_for(message.recipients()):
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
