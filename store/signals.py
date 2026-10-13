from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from accounts.signals import account_deleted
from store.models import Cart
from store.services import merge_session_cart_into_user_cart


@receiver(user_logged_in)
def merge_cart_after_login(sender, request, user, **kwargs):
    if request is None:
        return
    merge_session_cart_into_user_cart(
        request=request,
        user=user,
    )


@receiver(account_deleted)
def delete_cart_of_deleted_account(sender, user, **kwargs):
    # Корзина — не история покупок: при удалении аккаунта она не нужна.
    Cart.objects.filter(owner=user).delete()
