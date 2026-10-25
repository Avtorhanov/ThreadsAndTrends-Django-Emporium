from django.db import migrations, models


class Migration(migrations.Migration):
    """Тексты и блоки витрины, которые администратор правит прямо на сайте."""

    dependencies = [
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteText",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("key", models.CharField(max_length=80, unique=True, verbose_name="Ключ")),
                (
                    "value",
                    models.TextField(blank=True, max_length=2000, verbose_name="Текст"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменён")),
            ],
            options={
                "verbose_name": "Текст сайта",
                "verbose_name_plural": "Тексты сайта",
                "ordering": ["key"],
            },
        ),
        migrations.CreateModel(
            name="CustomizedArea",
            fields=[
                (
                    "area",
                    models.CharField(
                        choices=[("contacts", "Контакты"), ("help", "Помощь"), ("footer", "Подвал")],
                        max_length=20,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Изменённый раздел",
                "verbose_name_plural": "Изменённые разделы",
            },
        ),
        migrations.CreateModel(
            name="Block",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "area",
                    models.CharField(
                        choices=[("contacts", "Контакты"), ("help", "Помощь"), ("footer", "Подвал")],
                        max_length=20,
                        verbose_name="Раздел",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("link", "Ссылка"),
                            ("whatsapp", "WhatsApp"),
                            ("telegram", "Telegram"),
                            ("vk", "ВКонтакте"),
                            ("phone", "Телефон"),
                            ("email", "Почта"),
                        ],
                        default="link",
                        max_length=20,
                        verbose_name="Тип",
                    ),
                ),
                ("title", models.CharField(blank=True, max_length=80, verbose_name="Название")),
                (
                    "value",
                    models.CharField(max_length=300, verbose_name="Ссылка или значение"),
                ),
                ("note", models.CharField(blank=True, max_length=160, verbose_name="Подпись")),
                ("icon", models.CharField(blank=True, max_length=20, verbose_name="Значок")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Блок сайта",
                "verbose_name_plural": "Блоки сайта",
                "ordering": ["area", "position", "id"],
                "indexes": [
                    models.Index(fields=["area", "position"], name="block_area_position_idx")
                ],
            },
        ),
    ]
