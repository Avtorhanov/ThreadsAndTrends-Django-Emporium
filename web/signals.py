from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from store.models import Category, Product, ProductImage, ProductVariant

from . import catalog_cache


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
@receiver(post_save, sender=ProductVariant)
@receiver(post_delete, sender=ProductVariant)
@receiver(post_save, sender=ProductImage)
@receiver(post_delete, sender=ProductImage)
@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def reset_catalog_grids(sender, **kwargs):
    # Сразу и после commit: параллельный запрос мог закэшировать сетку до фиксации транзакции.
    catalog_cache.bump()
    transaction.on_commit(catalog_cache.bump)
