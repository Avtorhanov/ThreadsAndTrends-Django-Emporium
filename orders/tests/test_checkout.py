import pytest
from django.core import mail
from django.core.exceptions import ValidationError

from orders.models import (
    ChangedBy,
    DeliveryMethod,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
)
from orders.services import checkout as checkout_service
from orders.services.checkout import CheckoutInput, normalize_phone
from store.models import CartItem, Product, ProductVariant
from store.services import cart as cart_service
from store.services import catalog
from store.tests.factories import make_product

from .factories import make_order

pytestmark = pytest.mark.django_db


def courier_input(**overrides) -> CheckoutInput:
    data = {
        "delivery_method": DeliveryMethod.COURIER,
        "payment_method": PaymentMethod.ON_DELIVERY,
        "recipient_name": "  Иван   Петров ",
        "recipient_phone": "8 (900) 123-45-67",
        "delivery_address": "Москва, ул. Ленина, д. 1, кв. 2",
        "comment": "Позвонить за час",
    }
    data.update(overrides)
    return CheckoutInput(**data)


def codes(error: ValidationError) -> set[str]:
    return {e.code for e in error.error_list}


def stock(product, size=""):
    return ProductVariant.all_objects.get(product=product, size=size).stock


def test_checkout_creates_order_from_cart(
    filled_cart, shirt, cap, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        order, created = checkout_service.checkout(filled_cart, courier_input(), "key-00000001")

    assert created
    assert order.number.startswith("DD-") and int(order.number[3:]) >= 100001
    assert order.status == OrderStatus.CONFIRMED
    assert (order.items_total_kopecks, order.delivery_kopecks, order.total_kopecks) == (
        3_700_00,
        500_00,
        4_200_00,
    )
    assert order.recipient_name == "Иван Петров"
    assert order.recipient_phone == "+79001234567"
    assert order.comment == "Позвонить за час"

    items = {item.product_name: item for item in order.items.all()}
    assert set(items) == {"Футболка", "Кепка"}
    assert (items["Футболка"].size, items["Футболка"].quantity) == ("M", 2)
    assert items["Футболка"].price_kopecks == 1_500_00
    assert items["Кепка"].sku == cap.variants.get().sku

    assert stock(shirt, "M") == 3 and stock(shirt, "S") == 5 and stock(cap) == 2
    assert not CartItem.objects.filter(cart__owner=filled_cart).exists()

    history = list(order.status_changes.values_list("from_status", "to_status", "changed_by"))
    assert history == [("", OrderStatus.CONFIRMED, ChangedBy.CUSTOMER)]

    assert len(mail.outbox) == 1
    assert order.number in mail.outbox[0].subject
    assert "4\u00a0200" in mail.outbox[0].body


def test_order_total_equals_cart_total_shown_to_customer(filled_cart):
    shown = cart_service.get_summary(filled_cart).total_kopecks
    order, _ = checkout_service.checkout(filled_cart, courier_input(), "key-00000001")
    assert order.items_total_kopecks == shown


def test_online_payment_waits_for_payment(filled_cart):
    order, _ = checkout_service.checkout(
        filled_cart, courier_input(payment_method=PaymentMethod.ONLINE), "key-00000001"
    )
    assert order.status == OrderStatus.AWAITING_PAYMENT


def test_online_payment_can_be_disabled(filled_cart, settings):
    settings.ORDERS_ONLINE_PAYMENT_ENABLED = False
    assert checkout_service.payment_methods() == [PaymentMethod.ON_DELIVERY]
    with pytest.raises(ValidationError) as exc:
        checkout_service.checkout(
            filled_cart, courier_input(payment_method=PaymentMethod.ONLINE), "key-00000001"
        )
    assert "payment_method" in exc.value.message_dict


def test_free_courier_delivery_from_threshold(filled_cart, settings):
    settings.DELIVERY_FREE_FROM_KOPECKS = 3_700_00
    order, _ = checkout_service.checkout(filled_cart, courier_input(), "key-00000001")
    assert order.delivery_kopecks == 0 and order.total_kopecks == 3_700_00


def test_pickup_is_free_and_stores_pickup_address(filled_cart, settings):
    order, _ = checkout_service.checkout(
        filled_cart,
        courier_input(delivery_method=DeliveryMethod.PICKUP, delivery_address=""),
        "key-00000001",
    )
    assert order.delivery_kopecks == 0
    assert order.delivery_address == settings.PICKUP_ADDRESS


def test_pickup_unavailable_without_address(filled_cart, settings):
    settings.PICKUP_ADDRESS = ""
    with pytest.raises(ValidationError) as exc:
        checkout_service.checkout(
            filled_cart, courier_input(delivery_method=DeliveryMethod.PICKUP), "key-00000001"
        )
    assert "delivery_method" in exc.value.message_dict


def test_courier_requires_address_and_recipient(filled_cart):
    with pytest.raises(ValidationError) as exc:
        checkout_service.checkout(
            filled_cart,
            courier_input(delivery_address=" ", recipient_name="И", recipient_phone="123"),
            "key-00000001",
        )
    assert set(exc.value.message_dict) == {"delivery_address", "recipient_name", "recipient_phone"}
    assert not Order.objects.exists()


@pytest.mark.parametrize(
    "raw",
    ["+7 900 123-45-67", "89001234567", "8 (900) 123 45 67", "79001234567", "9001234567"],
)
def test_phone_is_normalized(raw):
    assert normalize_phone(raw) == "+79001234567"


@pytest.mark.parametrize("raw", ["", "12345", "+1 202 555 0100", "+7 900 123-45-6x", "1001234567"])
def test_invalid_phone_is_rejected(raw):
    with pytest.raises(ValidationError):
        normalize_phone(raw)


def test_repeat_with_same_key_returns_same_order(filled_cart, shirt):
    first, created_first = checkout_service.checkout(filled_cart, courier_input(), "key-00000001")
    second, created_second = checkout_service.checkout(filled_cart, courier_input(), "key-00000001")

    assert created_first and not created_second
    assert first.pk == second.pk
    assert Order.objects.count() == 1
    assert stock(shirt, "M") == 3  # списано один раз


@pytest.mark.parametrize("key", ["", "short", "x" * 65, "ключ-заказа-1"])
def test_idempotency_key_is_required(filled_cart, key):
    with pytest.raises(ValidationError) as exc:
        checkout_service.checkout(filled_cart, courier_input(), key)
    assert codes(exc.value) == {"idempotency_key"}


def test_empty_cart_is_rejected(customer):
    with pytest.raises(ValidationError) as exc:
        checkout_service.checkout(customer, courier_input(), "key-00000001")
    assert codes(exc.value) == {"empty_cart"}


@pytest.mark.parametrize(
    "spoil",
    [
        lambda shirt: ProductVariant.objects.filter(product=shirt, size="M").update(stock=1),
        lambda shirt: Product.objects.filter(pk=shirt.pk).update(is_active=False),
        lambda shirt: catalog.soft_delete_product(shirt),
    ],
    ids=["stock_dropped", "hidden", "deleted"],
)
def test_cart_with_problems_is_rejected(filled_cart, shirt, cap, spoil):
    spoil(shirt)

    with pytest.raises(ValidationError) as exc:
        checkout_service.checkout(filled_cart, courier_input(), "key-00000001")

    assert codes(exc.value) == {"cart_changed"}
    assert not Order.objects.exists()
    assert stock(cap) == 3
    assert CartItem.objects.filter(cart__owner=filled_cart).count() == 2


def test_changed_total_is_rejected(filled_cart, shirt):
    Product.objects.filter(pk=shirt.pk).update(price_kopecks=1_600_00)

    with pytest.raises(ValidationError) as exc:
        checkout_service.checkout(
            filled_cart, courier_input(expected_total_kopecks=4_200_00), "key-00000001"
        )
    assert codes(exc.value) == {"total_changed"}
    assert "4\u00a0400" in exc.value.messages[0]

    order, _ = checkout_service.checkout(
        filled_cart, courier_input(expected_total_kopecks=4_400_00), "key-00000002"
    )
    assert order.total_kopecks == 4_400_00


def test_order_numbers_are_unique(customer, shirt):
    numbers = []
    for n in range(3):
        cart_service.add(customer, shirt.variants.get(size="S").pk, 1)
        order, _ = checkout_service.checkout(customer, courier_input(), f"key-0000000{n}")
        numbers.append(int(order.number[3:]))
    assert numbers == sorted(set(numbers))


def test_history_survives_price_change_and_product_deletion(filled_cart, shirt):
    order, _ = checkout_service.checkout(filled_cart, courier_input(), "key-00000001")

    Product.objects.filter(pk=shirt.pk).update(price_kopecks=9_999_00, name="Другое")
    catalog.soft_delete_product(shirt)

    item = OrderItem.objects.select_related("product", "variant").get(
        order=order, sku=shirt.variants.model.all_objects.get(product=shirt, size="M").sku
    )
    assert (item.product_name, item.price_kopecks, item.size) == ("Футболка", 1_500_00, "M")
    assert item.product.pk == shirt.pk  # FK видит мягко удалённый товар


def test_preview_offers_options_and_last_recipient(customer, filled_cart, settings):
    make_order(
        customer,
        recipient_name="Пётр",
        recipient_phone="+79990000000",
        delivery_address="Казань, ул. Баумана, 5",
    )

    preview = checkout_service.preview(customer)

    assert preview.cart.total_kopecks == 3_700_00
    assert [(o.method, o.cost_kopecks) for o in preview.delivery_options] == [
        (DeliveryMethod.COURIER, 500_00),
        (DeliveryMethod.PICKUP, 0),
    ]
    assert preview.delivery_options[1].address == settings.PICKUP_ADDRESS
    assert preview.payment_methods == [PaymentMethod.ONLINE, PaymentMethod.ON_DELIVERY]
    assert preview.defaults.recipient_name == "Пётр"
    assert preview.defaults.delivery_address == "Казань, ул. Баумана, 5"


def test_preview_does_not_suggest_pickup_point_as_home_address(customer):
    make_order(customer, delivery_method=DeliveryMethod.PICKUP, delivery_address="Пункт выдачи")
    assert checkout_service.preview(customer).defaults.delivery_address == ""


def test_order_of_other_product_does_not_touch_foreign_stock(filled_cart):
    other = make_product(name="Шарф", stock=4)
    checkout_service.checkout(filled_cart, courier_input(), "key-00000001")
    assert stock(other) == 4
