# Сессия 4, шаг 1 из 3: позиция корзины ссылается на вариант товара (временно nullable).
# Данные переносит 0006, старые поля удаляет 0007.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0004_catalog_finalize"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartitem",
            name="variant",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cart_items",
                to="store.productvariant",
                verbose_name="Вариант товара",
            ),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="seen_price_kopecks",
            field=models.PositiveBigIntegerField(
                default=0, verbose_name="Цена, которую видел покупатель, коп."
            ),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="added_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now, verbose_name="Добавлено"
            ),
            preserve_default=False,
        ),
    ]
