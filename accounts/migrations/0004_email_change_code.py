import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_user_avatar"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailChangeCode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("new_email", models.EmailField(max_length=254, verbose_name="Новый email")),
                ("code_hash", models.CharField(max_length=64, verbose_name="HMAC кода")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("expires_at", models.DateTimeField(db_index=True, verbose_name="Действует до")),
                (
                    "attempts",
                    models.PositiveSmallIntegerField(default=0, verbose_name="Неудачных попыток"),
                ),
                (
                    "used_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Использован/аннулирован"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_change_codes",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Код смены email",
                "verbose_name_plural": "Коды смены email",
                "indexes": [
                    models.Index(
                        fields=["user", "-created_at"], name="email_code_user_created_idx"
                    )
                ],
            },
        ),
    ]
