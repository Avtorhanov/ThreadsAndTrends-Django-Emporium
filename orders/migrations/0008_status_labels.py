from django.db import migrations, models

# Подписи шагов обработки — как в панели и у покупателя: «В пути», «В пункте выдачи».
STATUS_CHOICES = [
    ("awaiting_payment", "Ожидает оплаты"),
    ("confirmed", "Принят"),
    ("paid", "Оплачен"),
    ("assembled", "Собран"),
    ("shipped", "В пути"),
    ("ready_for_pickup", "В пункте выдачи"),
    ("delivered", "Получен"),
    ("cancelled", "Отменён"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0007_orderitem_status_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(choices=STATUS_CHOICES, max_length=20, verbose_name="Статус"),
        ),
        migrations.AlterField(
            model_name="orderstatuschange",
            name="from_status",
            field=models.CharField(
                blank=True, choices=STATUS_CHOICES, max_length=20, verbose_name="Из статуса"
            ),
        ),
        migrations.AlterField(
            model_name="orderstatuschange",
            name="to_status",
            field=models.CharField(choices=STATUS_CHOICES, max_length=20, verbose_name="В статус"),
        ),
    ]
