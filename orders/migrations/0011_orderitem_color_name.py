from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0010_order_agreement"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="color_name",
            field=models.CharField(
                blank=True, db_default="", default="", max_length=40, verbose_name="Цвет"
            ),
        ),
    ]
