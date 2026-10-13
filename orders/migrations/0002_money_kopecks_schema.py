# Сессия 3: деньги заказов в копейках (шаг 1 из 3 — новые поля).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0001_initial"),
        ("store", "0004_catalog_finalize"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="total_kopecks",
            field=models.PositiveBigIntegerField(default=0, verbose_name="Общая стоимость, коп."),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="price_kopecks",
            field=models.PositiveBigIntegerField(default=0, verbose_name="Цена, коп."),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="store.product",
                verbose_name="Товар",
            ),
        ),
    ]
