from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    """Цена по запросу: price_kopecks может быть пустой (товар без цены не продаётся
    через корзину). Старая цена допустима только при заданной цене."""

    dependencies = [
        ("store", "0009_product_image_size_thumbs"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="product", name="product_price_positive"),
        migrations.RemoveConstraint(model_name="product", name="product_compare_at_gt_price"),
        migrations.AlterField(
            model_name="product",
            name="price_kopecks",
            field=models.PositiveBigIntegerField(
                blank=True, null=True, verbose_name="Цена, коп. (пусто — по запросу)"
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=Q(price_kopecks__isnull=True) | Q(price_kopecks__gt=0),
                name="product_price_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=Q(compare_at_kopecks__isnull=True)
                | Q(price_kopecks__isnull=False, compare_at_kopecks__gt=F("price_kopecks")),
                name="product_compare_at_gt_price",
            ),
        ),
    ]
