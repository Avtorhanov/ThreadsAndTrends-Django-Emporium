# Сессия 3: деньги заказов в копейках (шаг 3 из 3 — удаление DecimalField).

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0003_money_kopecks_data"),
    ]

    operations = [
        migrations.RemoveField(model_name="order", name="total_price"),
        migrations.RemoveField(model_name="orderitem", name="price"),
    ]
