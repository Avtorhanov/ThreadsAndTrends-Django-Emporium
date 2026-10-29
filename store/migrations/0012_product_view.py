import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0011_product_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductView",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "viewed_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Просмотрен"
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="store.product",
                        verbose_name="Товар",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_views",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Покупатель",
                    ),
                ),
            ],
            options={
                "verbose_name": "Просмотр товара",
                "verbose_name_plural": "Просмотры товаров",
                "indexes": [
                    models.Index(fields=["user", "-viewed_at"], name="product_view_recent_idx")
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "product"), name="product_view_unique"
                    )
                ],
            },
        ),
    ]
