from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0002_site_texts_blocks"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShopSettings",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "delivery_courier_kopecks",
                    models.PositiveBigIntegerField(
                        blank=True, null=True, verbose_name="Доставка курьером, коп."
                    ),
                ),
                (
                    "delivery_free_from_kopecks",
                    models.PositiveBigIntegerField(
                        blank=True, null=True, verbose_name="Бесплатная доставка от, коп."
                    ),
                ),
                ("pickup_enabled", models.BooleanField(default=True, verbose_name="Самовывоз")),
                (
                    "pickup_address",
                    models.CharField(
                        blank=True, max_length=300, verbose_name="Адрес пункта выдачи"
                    ),
                ),
                (
                    "cash_on_delivery_enabled",
                    models.BooleanField(default=True, verbose_name="Оплата при получении"),
                ),
                (
                    "unpaid_timeout_minutes",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Автоотмена неоплаченного заказа, мин"
                    ),
                ),
                (
                    "seller_name",
                    models.CharField(blank=True, max_length=200, verbose_name="Продавец"),
                ),
                ("seller_inn", models.CharField(blank=True, max_length=12, verbose_name="ИНН")),
                (
                    "seller_ogrn",
                    models.CharField(blank=True, max_length=15, verbose_name="ОГРН / ОГРНИП"),
                ),
                (
                    "seller_address",
                    models.CharField(blank=True, max_length=300, verbose_name="Адрес продавца"),
                ),
                (
                    "seller_phone",
                    models.CharField(blank=True, max_length=30, verbose_name="Телефон"),
                ),
                (
                    "seller_email",
                    models.EmailField(blank=True, max_length=254, verbose_name="Email"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменены")),
            ],
            options={
                "verbose_name": "Настройки магазина",
                "verbose_name_plural": "Настройки магазина",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("id", 1)), name="shop_settings_singleton"
                    )
                ],
            },
        ),
    ]
