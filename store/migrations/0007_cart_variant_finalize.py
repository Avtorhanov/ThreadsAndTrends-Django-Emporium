# Сессия 4, шаг 3 из 3: удаление снимка цены и ссылки на товар, одна корзина на пользователя.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0006_cart_variant_data"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="cartitem", name="unique_cart_product"),
        migrations.RemoveField(model_name="cart", name="products"),
        migrations.RemoveField(model_name="cart", name="session_key"),
        migrations.RemoveField(model_name="cartitem", name="product"),
        migrations.RemoveField(model_name="cartitem", name="price_kopecks"),
        migrations.AlterField(
            model_name="cart",
            name="owner",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cart",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Покупатель",
            ),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="cart",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="items",
                to="store.cart",
                verbose_name="Корзина",
            ),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="variant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cart_items",
                to="store.productvariant",
                verbose_name="Вариант товара",
            ),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="quantity",
            field=models.PositiveIntegerField(verbose_name="Количество"),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="seen_price_kopecks",
            field=models.PositiveBigIntegerField(
                verbose_name="Цена, которую видел покупатель, коп."
            ),
        ),
        migrations.AlterModelOptions(
            name="cart",
            options={"verbose_name": "Корзина", "verbose_name_plural": "Корзины"},
        ),
        migrations.AlterModelOptions(
            name="cartitem",
            options={
                "ordering": ["id"],
                "verbose_name": "Позиция корзины",
                "verbose_name_plural": "Позиции корзины",
            },
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(
                fields=("cart", "variant"), name="cart_item_unique_variant"
            ),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.CheckConstraint(
                condition=models.Q(("quantity__gte", 1)), name="cart_item_quantity_gte_1"
            ),
        ),
    ]
