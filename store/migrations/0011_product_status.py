import django.db.models.deletion
from django.db import migrations, models

# Стартовый справочник: администратор переименует или добавит свои в панели.
INITIAL = [
    ("В наличии", "Уже у нас — отправим сразу", "success"),
    ("Под заказ", "Привезём специально под заказ", "warning"),
    ("Ожидается поставка", "Скоро будет в наличии", "info"),
]


def create_statuses(apps, schema_editor):
    ProductStatus = apps.get_model("store", "ProductStatus")
    for position, (name, hint, tone) in enumerate(INITIAL):
        ProductStatus.objects.get_or_create(
            name=name, defaults={"hint": hint, "tone": tone, "position": position}
        )


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0010_product_price_on_request"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductStatus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=40, unique=True, verbose_name="Название")),
                (
                    "hint",
                    models.CharField(
                        blank=True, max_length=120, verbose_name="Подсказка покупателю"
                    ),
                ),
                (
                    "tone",
                    models.CharField(
                        choices=[
                            ("success", "Зелёный"),
                            ("warning", "Жёлтый"),
                            ("info", "Синий"),
                            ("neutral", "Серый"),
                        ],
                        default="neutral",
                        max_length=10,
                        verbose_name="Цвет",
                    ),
                ),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменён")),
            ],
            options={
                "verbose_name": "Статус товара",
                "verbose_name_plural": "Статусы товаров",
                "ordering": ["position", "id"],
            },
        ),
        migrations.AddField(
            model_name="product",
            name="status",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="store.productstatus",
                verbose_name="Статус",
            ),
        ),
        migrations.RunPython(create_statuses, migrations.RunPython.noop),
    ]
