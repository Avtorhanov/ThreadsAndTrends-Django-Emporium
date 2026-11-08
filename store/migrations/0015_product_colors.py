from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0014_product_agreement_channel"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="color_group",
            field=models.UUIDField(blank=True, null=True, verbose_name="Группа цветов"),
        ),
        migrations.AddField(
            model_name="product",
            name="color_name",
            field=models.CharField(
                blank=True, db_default="", default="", max_length=40, verbose_name="Цвет"
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(
                condition=models.Q(("color_group__isnull", False)),
                fields=["color_group"],
                name="product_color_group_idx",
            ),
        ),
    ]
