import re

import pytest
from django.urls import reverse

from orders.models import Order, OrderStatus, PaymentMethod
from orders.tests.factories import make_order
from payments.models import Payment, PaymentStatus
from store.models import CartItem, ProductVariant
from store.services import cart as cart_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def filled(customer, shop):
    """В корзине клиента: футболка M × 2 (1 990 ₽) — 3 980 ₽, доставка курьером 500 ₽."""
    variant = shop["shirt"].variants.get(size="M")
    cart_service.add(customer, variant.pk, 2)
    return variant


def checkout_form(client) -> dict:
    """Скрытые поля со страницы оформления, как их отправит браузер."""
    html = client.get(reverse("web:checkout")).content.decode()
    hidden = dict(re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', html))
    return {
        "expected_total": hidden["expected_total"],
        "idempotency_key": hidden["idempotency_key"],
        "delivery_method": "courier",
        "payment_method": "on_delivery",
        "recipient_name": "Иван Петров",
        "recipient_phone": "8 (900) 123-45-67",
        "delivery_address": "Москва, ул. Ленина, 1, кв. 1",
    }


def test_checkout_page(customer_client, filled):
    response = customer_client.get(reverse("web:checkout"))
    html = response.content.decode()
    assert response.status_code == 200
    assert 'name="expected_total" value="398000"' in html
    assert "4 480" in html  # итог с доставкой 500 ₽
    assert "Самовывоз" in html  # PICKUP_ADDRESS задан в тестах
    assert "Иван" in html  # получатель — из профиля


def test_checkout_redirects_with_empty_cart(customer_client, shop):
    response = customer_client.get(reverse("web:checkout"))
    assert response.status_code == 302 and response["Location"] == reverse("web:cart")


def test_checkout_on_delivery_creates_order(customer_client, customer, filled):
    response = customer_client.post(reverse("web:checkout"), checkout_form(customer_client))
    order = Order.objects.get(owner=customer)
    assert response.status_code == 302
    assert response["Location"] == reverse("web:order", args=[order.number])
    assert order.status == OrderStatus.CONFIRMED
    assert (order.items_total_kopecks, order.delivery_kopecks, order.total_kopecks) == (
        3_980_00,
        500_00,
        4_480_00,
    )
    assert order.recipient_phone == "+79001234567"
    filled.refresh_from_db()
    assert filled.stock == 3
    assert not CartItem.objects.filter(cart__owner=customer).exists()


def test_pickup_is_free(customer_client, customer, filled):
    data = {**checkout_form(customer_client), "delivery_method": "pickup", "delivery_address": ""}
    customer_client.post(reverse("web:checkout"), data)
    order = Order.objects.get(owner=customer)
    assert order.total_kopecks == 3_980_00 and order.delivery_kopecks == 0


def test_double_submit_creates_one_order(customer_client, customer, filled):
    data = checkout_form(customer_client)
    first = customer_client.post(reverse("web:checkout"), data)
    # Повтор после оформления: корзина уже пуста — страница оформления уводит в корзину,
    # но тот же ключ не создаёт второй заказ ни при каком повторе.
    cart_service.add(customer, filled.pk, 1)
    second = customer_client.post(reverse("web:checkout"), data)
    assert Order.objects.filter(owner=customer).count() == 1
    assert first["Location"] == second["Location"]


def test_price_change_after_render_is_reported(customer_client, customer, shop, filled):
    data = checkout_form(customer_client)
    shop["shirt"].price_kopecks = 2_190_00
    shop["shirt"].save()
    response = customer_client.post(reverse("web:checkout"), data)
    assert response.status_code == 200
    assert "Сумма заказа изменилась" in response.content.decode()
    assert not Order.objects.exists()


def test_invalid_fields_are_shown(customer_client, filled):
    data = {**checkout_form(customer_client), "recipient_phone": "123", "delivery_address": ""}
    html = customer_client.post(reverse("web:checkout"), data).content.decode()
    assert "Введите российский номер телефона" in html
    assert "Укажите адрес доставки" in html
    assert not Order.objects.exists()


def test_online_checkout_redirects_to_payment_page(
    customer_client, customer, filled, fake_provider
):
    data = {**checkout_form(customer_client), "payment_method": "online"}
    response = customer_client.post(reverse("web:checkout"), data)
    order = Order.objects.get(owner=customer)
    payment_id = fake_provider.only_payment_id()
    assert order.status == OrderStatus.AWAITING_PAYMENT
    assert response.status_code == 302
    assert response["Location"] == f"https://yoomoney.test/checkout?orderId={payment_id}"
    return_url = fake_provider.payments[payment_id]["return_url"]
    assert return_url == f"http://testserver/orders/{order.number}/?paid=1"

    # Покупатель оплатил и вернулся: страница заказа сверяет платёж с провайдером.
    fake_provider.pay(payment_id)
    html = customer_client.get(return_url).content.decode()
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID
    assert "Оплачено онлайн" in html


def test_payment_service_down_keeps_order(customer_client, customer, filled, fake_provider):
    fake_provider.down = True
    data = {**checkout_form(customer_client), "payment_method": "online"}
    response = customer_client.post(reverse("web:checkout"), data, follow=True)
    order = Order.objects.get(owner=customer)
    assert order.status == OrderStatus.AWAITING_PAYMENT
    html = response.content.decode()
    assert "Платёжный сервис временно недоступен" in html
    assert reverse("web:order_pay", args=[order.number]) in html  # можно повторить


def test_pay_again_reuses_pending_payment(customer_client, customer, fake_provider):
    order = make_order(
        customer, status=OrderStatus.AWAITING_PAYMENT, payment_method=PaymentMethod.ONLINE
    )
    url = reverse("web:order_pay", args=[order.number])
    first = customer_client.post(url)
    second = customer_client.post(url)
    assert first["Location"] == second["Location"]
    assert Payment.objects.filter(order=order, status=PaymentStatus.PENDING).count() == 1


def test_orders_list_and_detail(customer_client, customer):
    order = make_order(customer)
    html = customer_client.get(reverse("web:orders")).content.decode()
    assert order.number in html and "Принят" in html
    detail = customer_client.get(reverse("web:order", args=[order.number]))
    assert detail.status_code == 200
    assert "Иван Петров" in detail.content.decode()


def test_foreign_order_is_404(customer_client, other_customer):
    order = make_order(other_customer)
    for name in ("web:order", "web:order_cancel", "web:order_pay"):
        method = customer_client.get if name == "web:order" else customer_client.post
        assert method(reverse(name, args=[order.number])).status_code == 404


def test_cancel_order_returns_stock(customer_client, customer, shop):
    order = make_order(customer, shop["cap"], quantity=1)
    variant = ProductVariant.objects.get(pk=order.items.get().variant_id)
    stock = variant.stock
    response = customer_client.post(reverse("web:order_cancel", args=[order.number]))
    assert response.status_code == 302
    order.refresh_from_db()
    variant.refresh_from_db()
    assert order.status == OrderStatus.CANCELLED
    assert variant.stock == stock + 1


def test_cannot_cancel_shipped_order(customer_client, customer):
    order = make_order(customer, status=OrderStatus.SHIPPED)
    html = customer_client.get(reverse("web:order", args=[order.number])).content.decode()
    assert "Отменить заказ" not in html
    customer_client.post(reverse("web:order_cancel", args=[order.number]))
    order.refresh_from_db()
    assert order.status == OrderStatus.SHIPPED


def test_order_pages_query_count(customer_client, customer, django_assert_max_num_queries):
    order = make_order(customer)
    with django_assert_max_num_queries(16):
        customer_client.get(reverse("web:order", args=[order.number]))
    for _ in range(5):
        make_order(customer)
    with django_assert_max_num_queries(12):
        customer_client.get(reverse("web:orders"))


def test_buy_now_checkout_orders_only_that_item(customer_client, customer, shop, filled):
    cap = shop["cap"].variants.get()
    url = f"{reverse('web:checkout')}?variant={cap.pk}&qty=1"
    html = customer_client.get(url).content.decode()
    assert "Купить сейчас" in html and "Кепка" in html and "Футболка белая" not in html
    hidden = dict(re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', html))
    form = {
        "expected_total": hidden["expected_total"],
        "idempotency_key": hidden["idempotency_key"],
        "delivery_method": "courier",
        "payment_method": "on_delivery",
        "recipient_name": "Иван Петров",
        "recipient_phone": "8 (900) 123-45-67",
        "delivery_address": "Москва, ул. Ленина, 1, кв. 1",
    }
    response = customer_client.post(url, form)
    order = Order.objects.get(owner=customer)
    assert response.status_code == 302
    assert [(i.product_name, i.quantity) for i in order.items.all()] == [("Кепка", 1)]
    assert order.items_total_kopecks == 990_00
    # Корзина не тронута: футболка M × 2 осталась.
    assert list(CartItem.objects.values_list("variant_id", "quantity")) == [(filled.pk, 2)]


def test_buy_now_unavailable_returns_to_product(customer_client, shop):
    sold_out = shop["sold_out"].variants.get()
    response = customer_client.get(f"{reverse('web:checkout')}?variant={sold_out.pk}")
    assert response.status_code == 302
    assert response["Location"] == reverse("web:product", args=["hudi"])


def test_buy_now_guest_goes_to_login_and_back(client, shop):
    cap = shop["cap"].variants.get()
    url = f"{reverse('web:checkout')}?variant={cap.pk}&qty=1"
    response = client.get(url)
    assert response.status_code == 302 and "next=" in response["Location"]
    assert "variant" in response["Location"]


def test_buy_now_bad_params_404(customer_client, shop):
    assert customer_client.get(f"{reverse('web:checkout')}?variant=abc").status_code == 404
