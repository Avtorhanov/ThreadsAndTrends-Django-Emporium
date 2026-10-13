from django.urls import path

from . import views

# Подключаются под /api/v1/orders/ (оплата заказа клиентом).
order_payment_urlpatterns = [
    path("<str:number>/pay/", views.OrderPayView.as_view(), name="order-pay"),
    path(
        "<str:number>/pay/refresh/",
        views.OrderPaymentRefreshView.as_view(),
        name="order-pay-refresh",
    ),
]

# Подключаются под /api/v1/payments/ (уведомления провайдера).
payment_urlpatterns = [
    path("webhook/yookassa/", views.YooKassaWebhookView.as_view(), name="payments-webhook"),
]
