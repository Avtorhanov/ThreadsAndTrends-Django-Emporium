import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Создаёт администратора (суперпользователя) из ADMIN_EMAIL и ADMIN_PASSWORD, если его "
        "ещё нет. Пароль существующего пользователя не меняется."
    )

    def handle(self, *args, **options):
        email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("ADMIN_PASSWORD", "")
        if not email or not password:
            self.stdout.write("ADMIN_EMAIL/ADMIN_PASSWORD не заданы — администратор не создаётся.")
            return

        User = get_user_model()
        user = User.objects.filter(email=email).first()
        if user is not None:
            if not (user.is_staff and user.is_superuser and user.is_active):
                raise CommandError(
                    f"{email} уже зарегистрирован как клиент или отключён. Укажите другой "
                    "ADMIN_EMAIL или назначьте права в резервной админке."
                )
            self.stdout.write(f"Администратор {email} уже есть.")
            return

        candidate = User(email=email)
        try:
            validate_password(password, candidate)
        except ValidationError as exc:
            raise CommandError("ADMIN_PASSWORD слишком простой: " + " ".join(exc.messages)) from exc
        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Администратор {email} создан."))
