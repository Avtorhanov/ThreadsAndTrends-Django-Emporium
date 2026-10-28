import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffAccess",
            fields=[
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="staff_access",
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Сотрудник",
                    ),
                ),
                ("permissions", models.JSONField(default=dict, verbose_name="Права по разделам")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Приглашён")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменён")),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пригласил",
                    ),
                ),
            ],
            options={
                "verbose_name": "Права сотрудника",
                "verbose_name_plural": "Права сотрудников",
            },
        ),
    ]
