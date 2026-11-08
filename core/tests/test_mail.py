from smtplib import SMTPException
from unittest import mock

import pytest
from django.core.mail import EmailMessage

from core.mail import FailoverEmailBackend, relays_for
from core.tasks import RETRY_DELAYS, send_email

RELAYS = [
    {"name": "Яндекс", "host": "smtp.yandex.ru", "port": 465, "user": "a@ya.ru", "password": "p"},
    {
        "name": "Gmail",
        "host": "smtp.gmail.com",
        "port": 465,
        "user": "b@gmail.com",
        "password": "p",
    },
]


@pytest.fixture
def relays(settings):
    settings.EMAIL_RELAYS = RELAYS
    settings.DEFAULT_FROM_EMAIL = "DiDi-shop <noreply@localhost>"


def test_next_mailbox_used_when_first_fails(relays):
    message = EmailMessage("Тема", "Текст", None, ["c@example.com"])
    with mock.patch("core.mail.EmailBackend") as backend:
        backend.return_value.send_messages.side_effect = [SMTPException("лимит"), 1]
        assert FailoverEmailBackend().send_messages([message]) == 1
    assert backend.call_args_list[1].kwargs["host"] == "smtp.gmail.com"
    assert "b@gmail.com" in message.from_email


@pytest.mark.parametrize(
    "address, first",
    [
        ("c@gmail.com", "Gmail"),
        ("C@GOOGLEMAIL.COM", "Gmail"),
        ("c@ya.ru", "Яндекс"),
        ("c@example.com", "Яндекс"),
    ],
)
def test_recipient_service_goes_first(relays, address, first):
    assert [r["name"] for r in relays_for([address])][0] == first
    assert len(relays_for([address])) == 2


def test_missing_mailbox_falls_back_to_configured_order(relays):
    assert [r["name"] for r in relays_for(["c@mail.ru"])] == ["Яндекс", "Gmail"]


def test_error_raised_when_all_mailboxes_fail(relays):
    message = EmailMessage("Тема", "Текст", None, ["c@example.com"])
    with mock.patch("core.mail.EmailBackend") as backend:
        backend.return_value.send_messages.side_effect = OSError("сеть")
        with pytest.raises(OSError):
            FailoverEmailBackend().send_messages([message])
    assert backend.call_count == 2


def test_failed_email_is_retried_later():
    with (
        mock.patch("core.tasks.send_mail", side_effect=SMTPException("сбой")),
        mock.patch.object(type(send_email), "using") as using,
    ):
        send_email.func("Тема", "Текст", ["c@example.com"])
    using.return_value.enqueue.assert_called_once_with(
        "Тема", "Текст", ["c@example.com"], attempt=1
    )


def test_last_attempt_raises():
    with mock.patch("core.tasks.send_mail", side_effect=SMTPException("сбой")):
        with pytest.raises(SMTPException):
            send_email.func("Тема", "Текст", ["c@example.com"], attempt=len(RETRY_DELAYS))
