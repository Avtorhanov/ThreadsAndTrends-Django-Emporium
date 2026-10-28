from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0006_status_change_comment"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="status_name",
            field=models.CharField(blank=True, max_length=40, verbose_name="Статус товара"),
        ),
    ]
