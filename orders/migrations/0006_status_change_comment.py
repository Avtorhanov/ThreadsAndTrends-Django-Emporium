from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_orders_state_machine"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderstatuschange",
            name="comment",
            field=models.CharField(
                blank=True,
                help_text="Видит клиент в истории заказа и в письме",
                max_length=500,
                verbose_name="Комментарий для клиента",
            ),
        ),
        migrations.AddField(
            model_name="orderstatuschange",
            name="notified",
            field=models.BooleanField(default=False, verbose_name="Клиенту отправлено письмо"),
        ),
    ]
