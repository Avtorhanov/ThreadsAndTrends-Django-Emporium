from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0008_product_search_price_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="productimage",
            name="width",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="Ширина, px"),
        ),
        migrations.AddField(
            model_name="productimage",
            name="height",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="Высота, px"),
        ),
        migrations.AddField(
            model_name="productimage",
            name="thumbs_ready",
            field=models.BooleanField(default=False, verbose_name="Превью готовы"),
        ),
    ]
