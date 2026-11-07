from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0012_product_view"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_draft",
            field=models.BooleanField(db_default=False, default=False, verbose_name="Черновик"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                condition=Q(("deleted_at__isnull", True), ("is_draft", True)),
                fields=["-created_at"],
                name="product_draft_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=Q(("is_draft", False), ("is_active", False), _connector="OR"),
                name="product_draft_hidden",
            ),
        ),
    ]
