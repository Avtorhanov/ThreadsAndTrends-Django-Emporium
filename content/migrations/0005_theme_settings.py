from django.db import migrations, models

import content.models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0004_home_blocks"),
    ]

    operations = [
        migrations.CreateModel(
            name="ThemeSettings",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "palettes",
                    models.JSONField(
                        default=content.models.all_palettes, verbose_name="Доступные палитры"
                    ),
                ),
                (
                    "default_palette",
                    models.CharField(
                        default="lime", max_length=20, verbose_name="Палитра по умолчанию"
                    ),
                ),
                (
                    "default_mode",
                    models.CharField(
                        default="system", max_length=10, verbose_name="Тема по умолчанию"
                    ),
                ),
                (
                    "default_radius",
                    models.CharField(
                        default="normal", max_length=10, verbose_name="Углы по умолчанию"
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменены")),
            ],
            options={
                "verbose_name": "Тема магазина",
                "verbose_name_plural": "Тема магазина",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(id=1), name="theme_settings_singleton"
                    )
                ],
            },
        ),
    ]
