from django.db import migrations, models


class Migration(migrations.Migration):
    """Оферта скрыта, пока магазин не вырос; оператор ПДн — только для политики."""

    dependencies = [
        ("content", "0012_shop_settings_agreement"),
    ]

    operations = [
        migrations.AddField(
            model_name="shopsettings",
            name="offer_enabled",
            field=models.BooleanField(
                db_default=False, default=False, verbose_name="Показывать публичную оферту"
            ),
        ),
        migrations.AddField(
            model_name="shopsettings",
            name="operator_name",
            field=models.CharField(
                blank=True, db_default="", default="", max_length=200, verbose_name="Оператор данных"
            ),
        ),
        migrations.AddField(
            model_name="shopsettings",
            name="operator_contact",
            field=models.CharField(
                blank=True, db_default="", default="", max_length=200, verbose_name="Контакт для обращений"
            ),
        ),
    ]
