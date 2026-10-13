# Сессия 3, шаг 1 из 3: новые поля и модели каталога (временно nullable).
# Данные переносит 0003, старые поля удаляет 0004.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import store.models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0001_initial"),
    ]

    operations = [
        # --- Category: дерево вместо Category/SubCategory ---
        migrations.AlterField(
            model_name="category",
            name="name",
            field=models.CharField(max_length=100, verbose_name="Название"),
        ),
        migrations.AddField(
            model_name="category",
            name="slug",
            field=models.SlugField(max_length=120, null=True, verbose_name="Slug"),
        ),
        migrations.AddField(
            model_name="category",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="children",
                to="store.category",
                verbose_name="Родительская категория",
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Порядок"),
        ),
        migrations.AddField(
            model_name="category",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Показывать"),
        ),
        migrations.AddField(
            model_name="category",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now, verbose_name="Создана"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="category",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Изменена"),
        ),
        migrations.AlterModelOptions(
            name="category",
            options={
                "ordering": ["position", "name"],
                "verbose_name": "Категория",
                "verbose_name_plural": "Категории",
            },
        ),
        # --- Product ---
        migrations.RenameField(model_name="product", old_name="date", new_name="created_at"),
        migrations.AlterField(
            model_name="product",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Создан"),
        ),
        migrations.AlterField(
            model_name="product",
            name="name",
            field=models.CharField(max_length=200, verbose_name="Название"),
        ),
        migrations.AlterField(
            model_name="product",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AddField(
            model_name="product",
            name="slug",
            field=models.SlugField(max_length=220, null=True, verbose_name="Slug"),
        ),
        migrations.AddField(
            model_name="product",
            name="price_kopecks",
            field=models.PositiveBigIntegerField(null=True, verbose_name="Цена, коп."),
        ),
        migrations.AddField(
            model_name="product",
            name="compare_at_kopecks",
            field=models.PositiveBigIntegerField(
                blank=True, null=True, verbose_name="Старая цена, коп."
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Активен"),
        ),
        migrations.AddField(
            model_name="product",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Изменён"),
        ),
        migrations.AddField(
            model_name="product",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Удалён"),
        ),
        # --- Варианты и галерея ---
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("size", models.CharField(blank=True, max_length=50, verbose_name="Размер")),
                ("sku", models.CharField(max_length=64, verbose_name="Артикул")),
                ("stock", models.PositiveIntegerField(default=0, verbose_name="Остаток")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменён")),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Удалён"),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variants",
                        to="store.product",
                        verbose_name="Товар",
                    ),
                ),
            ],
            options={
                "verbose_name": "Вариант товара",
                "verbose_name_plural": "Варианты товара",
                "ordering": ["position", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("deleted_at__isnull", True)),
                        fields=("product", "size"),
                        name="variant_unique_size_per_product",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("deleted_at__isnull", True)),
                        fields=("sku",),
                        name="variant_unique_sku",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProductImage",
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
                        upload_to=store.models.product_image_path, verbose_name="Изображение"
                    ),
                ),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Загружено")),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="store.product",
                        verbose_name="Товар",
                    ),
                ),
            ],
            options={
                "verbose_name": "Изображение товара",
                "verbose_name_plural": "Изображения товара",
                "ordering": ["position", "id"],
            },
        ),
        # --- Корзина: снимок цены в копейках (сам снимок уберёт сессия 4) ---
        migrations.AddField(
            model_name="cartitem",
            name="price_kopecks",
            field=models.PositiveBigIntegerField(default=0, verbose_name="Цена, коп."),
        ),
    ]
