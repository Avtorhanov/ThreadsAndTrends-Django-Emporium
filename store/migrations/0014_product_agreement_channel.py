from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0013_product_draft"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="agreement_channel",
            field=models.CharField(
                blank=True,
                choices=[
                    ("whatsapp", "WhatsApp"),
                    ("telegram", "Telegram"),
                    ("vk", "ВКонтакте"),
                    ("phone", "Телефон"),
                ],
                db_default="",
                default="",
                max_length=20,
                verbose_name="Канал согласования",
            ),
        ),
    ]
