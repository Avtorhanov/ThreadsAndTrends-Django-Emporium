# Сессия 3: деньги заказов в копейках (шаг 2 из 3 — перенос значений).

from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations


def to_kopecks(value) -> int:
    if value is None:
        return 0
    return int((Decimal(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def forwards(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    OrderItem = apps.get_model("orders", "OrderItem")
    for order in Order.objects.all():
        order.total_kopecks = to_kopecks(order.total_price)
        order.save(update_fields=["total_kopecks"])
    for item in OrderItem.objects.all():
        item.price_kopecks = to_kopecks(item.price)
        item.save(update_fields=["price_kopecks"])


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0002_money_kopecks_schema"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
