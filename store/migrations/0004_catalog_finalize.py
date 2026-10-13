# Сессия 3, шаг 3 из 3: удаление старых полей, NOT NULL, уникальность, индексы, ограничения.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0003_catalog_data"),
    ]

    operations = [
        migrations.RemoveField(model_name="product", name="subcategory"),
        migrations.DeleteModel(name="SubCategory"),
        migrations.RemoveField(model_name="product", name="price"),
        migrations.RemoveField(model_name="product", name="image"),
        migrations.RemoveField(model_name="product", name="status"),
        migrations.RemoveField(model_name="cartitem", name="price"),
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=models.SlugField(max_length=120, unique=True, verbose_name="Slug"),
        ),
        migrations.AlterField(
            model_name="product",
            name="slug",
            field=models.SlugField(max_length=220, unique=True, verbose_name="Slug"),
        ),
        migrations.AlterField(
            model_name="product",
            name="price_kopecks",
            field=models.PositiveBigIntegerField(verbose_name="Цена, коп."),
        ),
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="store.category",
                verbose_name="Категория",
            ),
        ),
        migrations.AlterModelOptions(
            name="product",
            options={
                "ordering": ["-created_at", "-id"],
                "verbose_name": "Товар",
                "verbose_name_plural": "Товары",
            },
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["-created_at"], name="product_created_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                fields=["is_active", "deleted_at"], name="product_active_deleted_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                condition=models.Q(("deleted_at__isnull", True), ("is_active", True)),
                fields=["category", "-created_at"],
                name="product_live_category_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=models.Q(("price_kopecks__gt", 0)), name="product_price_positive"
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("compare_at_kopecks__isnull", True),
                    ("compare_at_kopecks__gt", models.F("price_kopecks")),
                    _connector="OR",
                ),
                name="product_compare_at_gt_price",
            ),
        ),
    ]
