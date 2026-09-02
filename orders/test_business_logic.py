from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.models import Order, OrderItem
from store.models import Cart, CartItem, Product


class OrdersBusinessLogicTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )

        self.product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=100,
        )

        self.product_2 = Product.objects.create(
            name="Test Product 2",
            description="Test Description 2",
            price=200,
        )

        self.cart = Cart.objects.create(
            owner=self.user,
        )

        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
            price=100,
        )

        self.cart_item_2 = CartItem.objects.create(
            cart=self.cart,
            product=self.product_2,
            quantity=1,
            price=200,
        )

    def test_checkout_creates_order_and_order_item(self):
        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        response = self.client.post(
            reverse(
                "checkout",
                args=[self.cart_item.id],
            ),
            {
                "full_name": "testuser",
                "address": "Test address",
                "phone_number": "+79999999999",
                "size": "M",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            Order.objects.filter(owner=self.user).count(),
            1,
        )

        order = Order.objects.get(owner=self.user)

        self.assertEqual(
            OrderItem.objects.filter(order=order).count(),
            1,
        )

        order_item = OrderItem.objects.get(order=order)

        self.assertEqual(
            order_item.product,
            self.product,
        )

        self.assertEqual(
            order_item.quantity,
            2,
        )

        self.assertEqual(
            order.total_price,
            200,
        )

    def test_checkout_removes_item_from_cart(self):
        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        cart_item_id = self.cart_item.id

        response = self.client.post(
            reverse(
                "checkout",
                args=[cart_item_id],
            ),
            {
                "full_name": "testuser",
                "address": "Test address",
                "phone_number": "+79999999999",
                "size": "M",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            CartItem.objects.filter(
                id=cart_item_id,
            ).exists()
        )

        self.assertTrue(
            CartItem.objects.filter(
                id=self.cart_item_2.id,
            ).exists()
        )

    def test_checkout_all_creates_order_with_all_cart_items(self):
        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        response = self.client.post(
            reverse("checkout_all"),
            {
                "full_name": "testuser",
                "address": "Test address",
                "phone_number": "+79999999999",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            Order.objects.filter(owner=self.user).count(),
            1,
        )

        order = Order.objects.get(owner=self.user)

        self.assertEqual(
            OrderItem.objects.filter(order=order).count(),
            2,
        )

        order_items = OrderItem.objects.filter(order=order)

        self.assertTrue(
            order_items.filter(product=self.product).exists()
        )

        self.assertTrue(
            order_items.filter(product=self.product_2).exists   ()
        )

        self.assertEqual(
            order.total_price,
            400,
        )

    def test_checkout_all_clears_cart(self):
        self.client.login(
            username="testuser",
            password="testpassword123",
        )
    
        response = self.client.post(
            reverse("checkout_all"),
            {
                "full_name": "testuser",
                "address": "Test address",
                "phone_number": "+79999999999",
            },
        )
    
        self.assertEqual(response.status_code, 302)
    
        self.assertFalse(
            CartItem.objects.filter(
                cart=self.cart,
            ).exists()
        )