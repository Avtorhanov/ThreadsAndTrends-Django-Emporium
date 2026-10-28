import django.db.models.deletion
from django.db import migrations, models

import content.models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0003_shop_settings"),
        ("store", "0011_product_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeImage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        upload_to=content.models.home_image_path, verbose_name="Изображение"
                    ),
                ),
                (
                    "width",
                    models.PositiveIntegerField(blank=True, null=True, verbose_name="Ширина, px"),
                ),
                (
                    "height",
                    models.PositiveIntegerField(blank=True, null=True, verbose_name="Высота, px"),
                ),
                (
                    "thumbs_ready",
                    models.BooleanField(default=False, verbose_name="Превью готовы"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Загружено"),
                ),
            ],
            options={
                "verbose_name": "Картинка главной",
                "verbose_name_plural": "Картинки главной",
            },
        ),
        migrations.CreateModel(
            name="HomePage",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "published",
                    models.JSONField(
                        blank=True, default=list, verbose_name="Опубликованные блоки"
                    ),
                ),
                (
                    "published_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Опубликована"),
                ),
                (
                    "changed_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Черновик изменён"),
                ),
            ],
            options={
                "verbose_name": "Главная",
                "verbose_name_plural": "Главная",
                "constraints": [
                    models.CheckConstraint(condition=models.Q(id=1), name="home_page_singleton")
                ],
            },
        ),
        migrations.CreateModel(
            name="HomeBlock",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("banner", "Баннер"),
                            ("collection", "Подборка товаров"),
                            ("categories", "Лента категорий"),
                            ("text", "Текст"),
                        ],
                        max_length=20,
                        verbose_name="Тип",
                    ),
                ),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("is_visible", models.BooleanField(default=True, verbose_name="Показывать")),
                (
                    "title",
                    models.CharField(blank=True, max_length=60, verbose_name="Заголовок"),
                ),
                ("text", models.CharField(blank=True, max_length=1000, verbose_name="Текст")),
                ("color", models.CharField(blank=True, max_length=7, verbose_name="Цвет")),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("new", "Новинки"),
                            ("category", "Категория"),
                            ("manual", "Вручную"),
                        ],
                        default="new",
                        max_length=10,
                        verbose_name="Какие товары",
                    ),
                ),
                (
                    "product_ids",
                    models.JSONField(blank=True, default=list, verbose_name="Товары"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="store.category",
                        verbose_name="Категория",
                    ),
                ),
                (
                    "image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="content.homeimage",
                        verbose_name="Изображение",
                    ),
                ),
            ],
            options={
                "verbose_name": "Блок главной",
                "verbose_name_plural": "Блоки главной",
                "ordering": ["position", "id"],
            },
        ),
    ]
