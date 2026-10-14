from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0007_cart_variant_finalize"),
    ]

    operations = [
        # Выражение совпадает с store.search.search_vector() — иначе индекс не используется.
        migrations.AddIndex(
            model_name="product",
            index=GinIndex(
                SearchVector("name", weight="A", config="russian")
                + SearchVector("description", weight="B", config="russian"),
                name="product_search_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["price_kopecks"], name="product_price_idx"),
        ),
    ]
