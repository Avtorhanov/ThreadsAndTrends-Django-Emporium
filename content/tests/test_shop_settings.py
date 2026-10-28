"""Настройки магазина из панели: доставка, оплата, реквизиты; пустое поле — значение из .env."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from content import shop
from content.models import ShopSettings
from orders.services import checkout

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "Str0ng-Passw0rd!"
URL = "/api/v1/admin/content/settings/"


@pytest.fixture
def staff(db):
    return User.objects.create_user(email="staff@example.com", password=PASSWORD, is_staff=True)


@pytest.fixture
def admin_api(staff):
    client = APIClient()
    client.force_login(staff)
    return client


@pytest.fixture
def env_seller(settings):
    settings.SELLER_NAME = ""
    settings.SELLER_INN = ""
    settings.SELLER_OGRN = ""
    settings.SELLER_ADDRESS = ""
    settings.SELLER_PHONE = ""
    settings.SELLER_EMAIL = ""


def payload(**changes) -> dict:
    data = {field: getattr(ShopSettings(), field) for field in shop.FIELDS}
    data.update(changes)
    return data


def test_defaults_come_from_env_until_saved(settings):
    current = shop.current()
    assert current.delivery_courier_kopecks == settings.DELIVERY_COURIER_KOPECKS
    assert current.delivery_free_from_kopecks == settings.DELIVERY_FREE_FROM_KOPECKS
    assert current.pickup_address == settings.PICKUP_ADDRESS
    assert current.unpaid_timeout_minutes == settings.ORDERS_UNPAID_TIMEOUT_MINUTES
    assert current.cash_on_delivery is True


def test_saved_values_override_env_and_empty_falls_back(settings):
    shop.update(
        **payload(delivery_courier_kopecks=300_00, pickup_address="  Казань,  ул. Баумана, 1 ")
    )
    current = shop.current()
    assert current.delivery_courier_kopecks == 300_00
    assert current.pickup_address == "Казань, ул. Баумана, 1"
    # Не заданное в панели — по-прежнему из .env.
    assert current.delivery_free_from_kopecks == settings.DELIVERY_FREE_FROM_KOPECKS

    shop.update(**payload(delivery_courier_kopecks=None, pickup_address=""))
    assert shop.current().delivery_courier_kopecks == settings.DELIVERY_COURIER_KOPECKS
    assert shop.current().pickup_address == settings.PICKUP_ADDRESS


def test_pickup_off_hides_pickup_option():
    shop.update(**payload(pickup_enabled=False))
    methods = [option.method for option in checkout.delivery_options(0)]
    assert methods == ["courier"]


def test_checkout_uses_panel_delivery_cost():
    shop.update(**payload(delivery_courier_kopecks=250_00, delivery_free_from_kopecks=5_000_00))
    assert checkout.delivery_cost("courier", 1_000_00) == 250_00
    assert checkout.delivery_cost("courier", 5_000_00) == 0


def test_cash_on_delivery_can_be_turned_off_only_with_online_payment(settings):
    settings.ORDERS_ONLINE_PAYMENT_ENABLED = False
    with pytest.raises(ValidationError) as error:
        shop.update(**payload(cash_on_delivery_enabled=False))
    assert "cash_on_delivery_enabled" in error.value.message_dict

    settings.ORDERS_ONLINE_PAYMENT_ENABLED = True
    shop.update(**payload(cash_on_delivery_enabled=False))
    assert checkout.payment_methods() == ["online"]

    # Онлайн-оплату выключили на сервере — оплата при получении возвращается сама.
    settings.ORDERS_ONLINE_PAYMENT_ENABLED = False
    assert checkout.payment_methods() == ["on_delivery"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("seller_inn", "12345"),
        ("seller_ogrn", "123"),
        ("seller_phone", "звоните"),
        ("seller_email", "не почта"),
        ("unpaid_timeout_minutes", 5),
        ("delivery_courier_kopecks", 1_000_000_00),
    ],
)
def test_invalid_values_rejected(field, value):
    with pytest.raises(ValidationError) as error:
        shop.update(**payload(**{field: value}))
    assert field in error.value.message_dict


def test_seller_parts_skip_empty_and_clean_values(env_seller):
    shop.update(
        **payload(
            seller_name="  ИП Иванов  И. И.,  ",
            seller_inn="7700 0000 0000",
            seller_ogrn="",
            seller_phone="+7 900 123-45-67",
        )
    )
    parts = shop.current().seller.parts()
    assert [part.text for part in parts] == [
        "ИП Иванов И. И.",
        "ИНН 770000000000",
        "+7 900 123-45-67",
    ]
    assert parts[2].href == "tel:+79001234567"


@pytest.mark.parametrize(
    ("ogrn", "label"), [("1027700132195", "ОГРН"), ("304500116000157", "ОГРНИП")]
)
def test_ogrn_label_by_length(env_seller, ogrn, label):
    shop.update(**payload(seller_name="Продавец", seller_ogrn=ogrn))
    assert shop.current().seller.parts()[1].text == f"{label} {ogrn}"


def test_footer_one_line_without_empty_fields(client, env_seller):
    html = client.get(reverse("web:home")).content.decode()
    assert "foot__seller" not in html  # ничего не заполнено — строки нет

    shop.update(**payload(seller_name="ИП Пример", seller_email="shop@example.com"))
    html = client.get(reverse("web:home")).content.decode()
    line = html.split('class="foot__seller"')[1].split("</p>")[0]
    assert "ИП Пример" in line and 'href="mailto:shop@example.com"' in line
    assert "ИНН" not in line and "<br>" not in line
    assert "&nbsp;· " in line


# --- API панели ---


def test_api_requires_admin(client, db):
    assert APIClient().get(URL).status_code in (401, 403)
    customer = User.objects.create_user(email="c@example.com", password=PASSWORD)
    api = APIClient()
    api.force_login(customer)
    assert api.get(URL).status_code == 403


def test_api_get_returns_defaults_and_put_saves(admin_api, settings):
    data = admin_api.get(URL).json()
    assert data["delivery_courier_kopecks"] is None
    assert data["defaults"]["delivery_courier_kopecks"] == settings.DELIVERY_COURIER_KOPECKS
    assert data["online_payment_available"] is True

    response = admin_api.put(URL, payload(delivery_courier_kopecks=400_00), format="json")
    assert response.status_code == 200, response.content
    assert response.json()["delivery_courier_kopecks"] == 400_00
    assert ShopSettings.objects.get().delivery_courier_kopecks == 400_00


def test_api_validation_error_is_400(admin_api):
    response = admin_api.put(URL, payload(seller_inn="1"), format="json")
    assert response.status_code == 400
    assert "seller_inn" in response.json()
