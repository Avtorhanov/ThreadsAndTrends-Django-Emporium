from django.dispatch import receiver

from accounts.signals import account_deleted
from store.models import Cart


@receiver(account_deleted)
def delete_cart_of_deleted_account(sender, user, **kwargs):
    # Корзина — не история покупок: при удалении аккаунта она не нужна.
    Cart.objects.filter(owner=user).delete()
