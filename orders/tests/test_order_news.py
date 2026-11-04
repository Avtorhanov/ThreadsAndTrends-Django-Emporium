"""Точка «есть новости по заказу»: магазин сменил статус — покупатель видит её на «Профиле»,
пока не откроет заказ (сайт или приложение)."""

import pytest
from django.urls import reverse

from orders.models import ChangedBy, Order, OrderStatus
from orders.services import status as status_service

from .factories import make_order

pytestmark = pytest.mark.django_db

S = OrderStatus


def test_admin_and_system_changes_mark_unseen(customer, staff):
    order = make_order(customer, status=S.CONFIRMED)
    assert not status_service.has_unseen(customer)

    status_service.transition(order, S.ASSEMBLED, by=ChangedBy.ADMIN, actor=staff, notify=False)
    assert Order.objects.get(pk=order.pk).status_unseen
    assert status_service.has_unseen(customer)

    paid = make_order(customer, status=S.AWAITING_PAYMENT)
    status_service.mark_seen(Order.objects.get(pk=order.pk))
    status_service.mark_paid(paid)
    assert Order.objects.get(pk=paid.pk).status_unseen


def test_customer_cancel_is_not_news(customer):
    order = make_order(customer, status=S.CONFIRMED)
    status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=customer)
    assert not Order.objects.get(pk=order.pk).status_unseen
    assert not status_service.has_unseen(customer)


def test_only_own_orders_count(customer, other_customer, staff):
    order = make_order(other_customer, status=S.CONFIRMED)
    status_service.transition(order, S.ASSEMBLED, by=ChangedBy.ADMIN, actor=staff, notify=False)
    assert not status_service.has_unseen(customer)
    assert status_service.has_unseen(other_customer)
    assert not status_service.has_unseen(staff)


def test_api_detail_marks_seen_and_profile_flag(client_api, customer, staff):
    order = make_order(customer, status=S.CONFIRMED)
    status_service.transition(order, S.ASSEMBLED, by=ChangedBy.ADMIN, actor=staff, notify=False)

    assert client_api.get("/api/v1/auth/me/").json()["has_order_news"] is True
    listed = client_api.get("/api/v1/orders/").json()["results"][0]
    assert listed["status_unseen"] is True

    assert client_api.get(f"/api/v1/orders/{order.number}/").status_code == 200
    assert not Order.objects.get(pk=order.pk).status_unseen
    assert client_api.get("/api/v1/auth/me/").json()["has_order_news"] is False


def test_api_detail_of_foreign_order_does_not_touch_flag(client_api, other_customer, staff):
    order = make_order(other_customer, status=S.CONFIRMED)
    status_service.transition(order, S.ASSEMBLED, by=ChangedBy.ADMIN, actor=staff, notify=False)
    assert client_api.get(f"/api/v1/orders/{order.number}/").status_code == 404
    assert Order.objects.get(pk=order.pk).status_unseen


def test_site_shows_dot_until_order_opened(client, customer, staff):
    order = make_order(customer, status=S.CONFIRMED)
    status_service.transition(order, S.ASSEMBLED, by=ChangedBy.ADMIN, actor=staff, notify=False)
    client.force_login(customer)

    home = client.get(reverse("web:home")).content.decode()
    assert 'class="news-dot"' in home

    detail = client.get(reverse("web:order", args=[order.number])).content.decode()
    assert 'class="news-dot"' not in detail
    assert not Order.objects.get(pk=order.pk).status_unseen
    assert 'class="news-dot"' not in client.get(reverse("web:home")).content.decode()
