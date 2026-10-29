from django.contrib.sitemaps.views import sitemap
from django.urls import path

from .seo import SITEMAPS
from .views import account, cart, catalog, content, orders, pages

app_name = "web"

urlpatterns = [
    # Каталог (адреса легаси-витрины сохранены: /products/, /category/<slug>/, /product/<slug>/).
    path("", catalog.home, name="home"),
    path("products/", catalog.products, name="products"),
    path("search/", catalog.search, name="search"),
    path("category/<slug:slug>/", catalog.category, name="category"),
    path("product/<slug:slug>/", catalog.product, name="product"),
    # Контакты и статьи
    path("contacts/", content.contacts, name="contacts"),
    path("articles/<slug:slug>/", content.article, name="article"),
    # Корзина
    path("cart/", cart.cart_page, name="cart"),
    path("cart/add/", cart.add, name="cart_add"),
    path("buy-now/", cart.buy_now, name="buy_now"),
    path("cart/line/<int:variant_id>/", cart.line, name="cart_line"),
    path("cart/ack-prices/", cart.ack_prices, name="cart_ack_prices"),
    # Оформление и заказы
    path("checkout/", orders.checkout, name="checkout"),
    path("orders/", orders.order_list, name="orders"),
    path("orders/<str:number>/", orders.order_detail, name="order"),
    path("orders/<str:number>/pay/", orders.pay, name="order_pay"),
    path("orders/<str:number>/cancel/", orders.order_cancel, name="order_cancel"),
    # Аккаунт
    path("login/", account.login_view, name="login"),
    path("logout/", account.logout_view, name="logout"),
    path("register/", account.register, name="register"),
    path("password-reset/", account.password_reset, name="password_reset"),
    path("password-reset/confirm/", account.password_reset_confirm, name="password_reset_confirm"),
    path("profile/", account.profile, name="profile"),
    path("profile/data/", account.profile_data, name="profile_data"),
    path("profile/avatar/", account.avatar, name="avatar"),
    path("profile/look/", account.profile_look, name="profile_look"),
    path("profile/viewed/clear/", account.viewed_clear, name="viewed_clear"),
    path("profile/password/", account.password_change, name="password_change"),
    path("profile/delete/", account.delete_account, name="delete_account"),
    # Служебные
    path("theme/", pages.set_theme, name="theme"),
    path("banner/hide/", pages.hide_banner, name="hide_banner"),
    path("legal/offer/", pages.legal, {"page": "offer"}, name="offer"),
    path("legal/privacy/", pages.legal, {"page": "privacy"}, name="privacy"),
    path("legal/delivery/", pages.legal, {"page": "delivery"}, name="delivery"),
    path("robots.txt", pages.robots_txt, name="robots"),
    path("manifest.webmanifest", pages.manifest, name="manifest"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
]
