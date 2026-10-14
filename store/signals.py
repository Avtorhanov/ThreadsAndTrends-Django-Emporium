from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from accounts.signals import account_deleted
from store.models import Cart, Category
from store.services.storefront import invalidate_category_tree


@receiver(account_deleted)
def delete_cart_of_deleted_account(sender, user, **kwargs):
    # Корзина — не история покупок: при удалении аккаунта она не нужна.
    Cart.objects.filter(owner=user).delete()


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def reset_category_tree_cache(sender, **kwargs):
    # Сразу и после commit: иначе параллельный запрос успеет закэшировать дерево
    # до фиксации транзакции.
    invalidate_category_tree()
    transaction.on_commit(invalidate_category_tree)
