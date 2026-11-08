from django.db import migrations, models

CHANNEL_CHOICES = [
    ("whatsapp", "WhatsApp"),
    ("telegram", "Telegram"),
    ("vk", "ВКонтакте"),
    ("phone", "Телефон"),
]


class Migration(migrations.Migration):
    """Оформление «по согласованию с продавцом» в мессенджере; онлайн-оплата — переключателем
    в панели (при подключённой ЮKassa); оплата при получении по умолчанию выключена."""

    dependencies = [
        ("content", "0011_theme_wordmark_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shopsettings",
            name="cash_on_delivery_enabled",
            field=models.BooleanField(default=False, verbose_name="Оплата при получении"),
        ),
        migrations.AddField(
            model_name="shopsettings",
            name="online_payment_enabled",
            field=models.BooleanField(blank=True, null=True, verbose_name="Онлайн-оплата ЮKassa"),
        ),
        migrations.AddField(
            model_name="shopsettings",
            name="agreement_enabled",
            field=models.BooleanField(
                db_default=True,
                default=True,
                verbose_name="Согласование с продавцом в мессенджере",
            ),
        ),
        migrations.AddField(
            model_name="shopsettings",
            name="agreement_channel",
            field=models.CharField(
                choices=CHANNEL_CHOICES,
                db_default="whatsapp",
                default="whatsapp",
                max_length=20,
                verbose_name="Канал согласования",
            ),
        ),
        migrations.AddField(
            model_name="shopsettings",
            name="agreement_timeout_hours",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="Автоотмена несогласованного заказа, ч"
            ),
        ),
    ]
