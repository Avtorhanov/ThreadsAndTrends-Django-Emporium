"""Оформление «по согласованию с продавцом»: заказ ждёт подтверждения, покупатель пишет продавцу
в мессенджер готовым текстом, продавец подтверждает в панели; несогласованный — отменяется."""

from datetime import timedelta
from urllib.parse import unquote

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from content import shop
from content.models import ShopSettings
from orders.models import ChangedBy, DeliveryMethod, Order, OrderStatus, PaymentMethod
from orders.services import agreement
from orders.services import checkout as checkout_service
from orders.services import status as status_service
from orders.services.checkout import CheckoutInput
from store.models import ProductVariant
from store.services import cart as cart_service
from store.tests.factories import make_product

pytestmark = pytest.mark.django_db

BASE = "https://shop.example.ru"
ORDER_API = "/api/v1/orders/{}/"


@pytest.fixture(autouse=True)
def contacts(settings):
    settings.CONTACT_WHATSAPP = "+7 900 111-22-33"
    settings.CONTACT_TELEGRAM = "@didishop"
    settings.CONTACT_VK = ""
    settings.SELLER_PHONE = "+7 900 444-55-66"


def agreement_input(**overrides) -> CheckoutInput:
    data = {
        "delivery_method": DeliveryMethod.COURIER,
        "payment_method": PaymentMethod.AGREEMENT,
        "recipient_name": "Иван Петров",
        "recipient_phone": "+79001234567",
        "delivery_address": "Москва, ул. Ленина, 1, кв. 2",
    }
    data.update(overrides)
    return CheckoutInput(**data)


def place(user, key="agree-key-0001") -> Order:
    order, _ = checkout_service.checkout(user, agreement_input(), key)
    return order


def stock(product, size=""):
    return ProductVariant.all_objects.get(product=product, size=size).stock


def set_shop(**values):
    row = ShopSettings.objects.filter(pk=1).first() or ShopSettings(pk=1)
    current = {field: getattr(row, field) for field in shop.FIELDS}
    shop.update(**{**current, **values})


def test_default_checkout_is_agreement_only(settings):
    settings.ORDERS_ONLINE_PAYMENT_ENABLED = False
    assert checkout_service.payment_methods() == [PaymentMethod.AGREEMENT]


def test_agreement_order_waits_and_reserves_stock(
    filled_cart, shirt, cap, settings, django_capture_on_commit_callbacks
):
    settings.SELLER_EMAIL = "seller@example.com"
    with django_capture_on_commit_callbacks(execute=True):
        order = place(filled_cart)

    assert order.status == OrderStatus.AWAITING_AGREEMENT
    assert order.payment_method == PaymentMethod.AGREEMENT
    assert order.agreement_channel == "whatsapp"
    assert stock(shirt, "M") == 3 and stock(cap) == 2  # товар отложен для покупателя

    recipients = sorted(m.to[0] for m in mail.outbox)
    assert recipients == ["customer@example.com", "seller@example.com"]
    customer_mail = next(m for m in mail.outbox if m.to == ["customer@example.com"])
    assert "напишите продавцу" in customer_mail.subject
    seller_mail = next(m for m in mail.outbox if m.to == ["seller@example.com"])
    assert order.number in seller_mail.subject and "Принят" in seller_mail.body


def test_no_seller_mail_without_seller_email(
    filled_cart, settings, django_capture_on_commit_callbacks
):
    settings.SELLER_EMAIL = ""
    with django_capture_on_commit_callbacks(execute=True):
        place(filled_cart)
    assert [m.to for m in mail.outbox] == [["customer@example.com"]]


def test_product_channel_overrides_shop_channel(customer):
    tg = make_product(name="Куртка", agreement_channel="telegram")
    tg2 = make_product(name="Шарф", agreement_channel="telegram")
    plain = make_product(name="Носки")

    cart_service.add(customer, tg.variants.get().pk, 1)
    cart_service.add(customer, tg2.variants.get().pk, 1)
    assert place(customer, "agree-key-0001").agreement_channel == "telegram"

    # Разные каналы в одном заказе — канал магазина.
    cart_service.add(customer, tg.variants.get().pk, 1)
    cart_service.add(customer, plain.variants.get().pk, 1)
    assert place(customer, "agree-key-0002").agreement_channel == "whatsapp"


def test_whatsapp_link_carries_message(filled_cart, shirt):
    order = place(filled_cart)
    found = agreement.link(order, BASE)

    assert found.kind == "whatsapp" and found.prefilled
    assert found.url.startswith("https://wa.me/79001112233?text=")
    text = unquote(found.url.split("text=", 1)[1])
    assert text == found.message
    assert order.number in text
    assert f"{BASE}/product/{shirt.slug}/" in text
    assert "Футболка, M × 2" in text and "Итого: 4 200 ₽" in text
    assert found.deadline == order.created_at + timedelta(hours=48)


def test_telegram_and_phone_links_are_not_prefilled(filled_cart):
    set_shop(agreement_channel="telegram")
    order = place(filled_cart)
    found = agreement.link(order, BASE)
    assert (found.kind, found.url, found.prefilled) == ("telegram", "https://t.me/didishop", False)

    Order.objects.filter(pk=order.pk).update(agreement_channel="phone")
    order.refresh_from_db()
    found = agreement.link(order, BASE)
    assert (found.kind, found.url) == ("phone", "tel:+79004445566")


def test_missing_channel_falls_back_to_first_configured(filled_cart, settings):
    set_shop(agreement_channel="vk")  # ВКонтакте у магазина не задан
    order = place(filled_cart)
    assert agreement.link(order, BASE).kind == "whatsapp"

    settings.CONTACT_WHATSAPP = settings.CONTACT_TELEGRAM = settings.SELLER_PHONE = ""
    assert agreement.link(order, BASE) is None


def test_admin_confirms_after_agreement(filled_cart, staff, django_capture_on_commit_callbacks):
    order = place(filled_cart)
    assert status_service.allowed_transitions(order, ChangedBy.ADMIN) == [
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED,
    ]
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        order = status_service.transition(
            order, OrderStatus.CONFIRMED, by=ChangedBy.ADMIN, actor=staff
        )

    assert order.status == OrderStatus.CONFIRMED and order.status_unseen
    assert agreement.link(order, BASE) is None
    assert len(mail.outbox) == 1 and "принят" in mail.outbox[0].subject
    # Дальше — обычный путь заказа.
    assert OrderStatus.ASSEMBLED in status_service.allowed_transitions(order, ChangedBy.ADMIN)


def test_customer_can_cancel_and_stock_returns(filled_cart, shirt):
    order = place(filled_cart)
    assert status_service.can_cancel(order, ChangedBy.CUSTOMER)
    status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=filled_cart)
    assert stock(shirt, "M") == 5


def test_stale_agreement_is_cancelled(filled_cart, shirt, customer):
    stale = place(filled_cart, "agree-key-0001")
    Order.objects.filter(pk=stale.pk).update(created_at=timezone.now() - timedelta(hours=49))
    cart_service.add(customer, shirt.variants.get(size="S").pk, 1)
    fresh = place(customer, "agree-key-0002")

    assert agreement.cancel_stale() == 1
    stale.refresh_from_db()
    fresh.refresh_from_db()
    assert stale.status == OrderStatus.CANCELLED
    assert fresh.status == OrderStatus.AWAITING_AGREEMENT
    assert stock(shirt, "M") == 5  # отложенный товар вернулся в продажу
    change = stale.status_changes.get(to_status=OrderStatus.CANCELLED)
    assert change.changed_by == ChangedBy.SYSTEM and "48 ч" in change.comment


def test_confirmed_order_is_never_auto_cancelled(filled_cart, staff):
    order = place(filled_cart)
    status_service.transition(order, OrderStatus.CONFIRMED, by=ChangedBy.ADMIN, actor=staff)
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=5))
    assert agreement.cancel_stale() == 0
    order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED


def test_timeout_from_panel(filled_cart):
    set_shop(agreement_timeout_hours=2)
    order = place(filled_cart)
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(hours=3))
    assert agreement.cancel_stale() == 1


def test_api_order_detail_has_agreement(filled_cart, client_api, settings):
    settings.SITE_URL = BASE
    order = place(filled_cart)
    body = client_api.get(ORDER_API.format(order.number)).json()

    assert body["status"] == "awaiting_agreement"
    assert body["status_display"] == "Ждёт согласования"
    assert body["agreement_channel"] == "whatsapp"
    assert body["agreement"]["kind"] == "whatsapp" and body["agreement"]["prefilled"] is True
    assert order.number in body["agreement"]["message"]
    assert body["can_cancel"] is True


def test_web_order_page_shows_contact_button(filled_cart, client):
    client.force_login(filled_cart)
    order = place(filled_cart)
    html = client.get(reverse("web:order", args=[order.number])).content.decode()

    assert "Согласуйте заказ с продавцом" in html
    assert "Написать в WhatsApp" in html
    assert 'href="https://wa.me/79001112233?text=' in html


def test_summary_counts_agreement_orders_outside_turnover(filled_cart):
    from orders.api.admin_summary import build_summary

    place(filled_cart)
    summary = build_summary()
    assert summary["awaiting_agreement"] == 1
    assert summary["today"]["turnover_kopecks"] == 0
