from django.db import migrations, models

# Оплата «по согласованию с продавцом»: статус «Ждёт согласования» и канал на момент оформления.
STATUS_CHOICES = [
    ("awaiting_payment", "Ожидает оплаты"),
    ("awaiting_agreement", "Ждёт согласования"),
    ("confirmed", "Принят"),
    ("paid", "Оплачен"),
    ("assembled", "Собран"),
    ("shipped", "В пути"),
    ("ready_for_pickup", "В пункте выдачи"),
    ("delivered", "Получен"),
    ("cancelled", "Отменён"),
]
PAYMENT_CHOICES = [
    ("online", "Онлайн"),
    ("agreement", "По согласованию с продавцом"),
    ("on_delivery", "При получении"),
]
CHANNEL_CHOICES = [
    ("whatsapp", "WhatsApp"),
    ("telegram", "Telegram"),
    ("vk", "ВКонтакте"),
    ("phone", "Телефон"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0009_order_status_unseen"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(choices=STATUS_CHOICES, max_length=20, verbose_name="Статус"),
        ),
        migrations.AlterField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=PAYMENT_CHOICES, max_length=20, verbose_name="Способ оплаты"
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="agreement_channel",
            field=models.CharField(
                blank=True,
                choices=CHANNEL_CHOICES,
                db_default="",
                default="",
                max_length=20,
                verbose_name="Канал согласования",
            ),
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
