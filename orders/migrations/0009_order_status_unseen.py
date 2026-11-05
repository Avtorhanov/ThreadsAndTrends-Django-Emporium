from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0008_status_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="status_unseen",
            field=models.BooleanField(
                db_default=False, default=False, verbose_name="Смена статуса не просмотрена"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                condition=Q(status_unseen=True), fields=["owner"], name="order_owner_unseen_idx"
            ),
        ),
    ]
