"""Сервисный слой магазина: cart — легаси-корзина (переписывается в сессии 4),
catalog — управление каталогом."""

from store.services.cart import (
    add_product_to_cart,
    get_cart,
    merge_session_cart_into_user_cart,
)

__all__ = ["add_product_to_cart", "get_cart", "merge_session_cart_into_user_cart"]
