from django.db import migrations, models


class Migration(migrations.Migration):
    """Текст всплывающего сообщения, когда размера больше нет."""

    dependencies = [
        ("content", "0013_shop_settings_offer_operator"),
    ]

    operations = [
        migrations.AddField(
            model_name="shopsettings",
            name="stock_limit_text",
            field=models.CharField(
                blank=True,
                db_default="",
                default="",
                max_length=120,
                verbose_name="Сообщение, когда больше нет",
            ),
        ),
    ]
