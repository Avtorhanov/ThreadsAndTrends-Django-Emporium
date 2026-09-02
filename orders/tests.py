from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from orders.models import Order
from store.models import Cart, CartItem, Product


class OrdersSecurityTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            password="testpassword123",
        )

        self.other_user = User.objects.create_user(
            username="other_user",
            password="testpassword123",
        )

        self.product = Product.objects.create(
            name="Test Product",
            description="Test Description",
            price=100,
        )

        self.owner_cart = Cart.objects.create(
            owner=self.owner,
        )

        self.other_cart = Cart.objects.create(
            owner=self.other_user,
        )

        self.owner_cart_item = CartItem.objects.create(
            cart=self.owner_cart,
            product=self.product,
            quantity=1,
            price=100,
        )

        self.other_cart_item = CartItem.objects.create(
            cart=self.other_cart,
            product=self.product,
            quantity=1,
            price=100,
        )

        self.owner_order = Order.objects.create(
            owner=self.owner,
            order_number="1",
            total_price=100,
            address="Owner Address",
            phone_number="+79999999999",
            full_name="owner",
            is_ordered=True,
        )

        self.other_order = Order.objects.create(
            owner=self.other_user,
            order_number="1",
            total_price=100,
            address="Other Address",
            phone_number="+78888888888",
            full_name="other_user",
            is_ordered=True,
        )

    # -------------------------------------------------
    # Authentication
    # -------------------------------------------------

    def test_anonymous_user_cannot_access_checkout(self):
        response = self.client.get(
            reverse(
                "checkout",
                args=[self.owner_cart_item.id],
            )
        )

        self.assertEqual(response.status_code, 302)

    def test_anonymous_user_cannot_access_order_detail(self):
        response = self.client.get(
            reverse(
                "order_detail",
                args=[self.owner_order.id],
            )
        )

        self.assertEqual(response.status_code, 302)

    def test_anonymous_user_cannot_delete_order(self):
        response = self.client.post(
            reverse(
                "delete_order",
                args=[self.owner_order.id],
            )
        )

        self.assertEqual(response.status_code, 302)

    # -------------------------------------------------
    # IDOR protection
    # -------------------------------------------------
    def test_delete_order_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        csrf_client.login(
            username="owner",
            password="testpassword123",
        )

        response = csrf_client.post(
            reverse(
                "delete_order",
                args=[self.owner_order.id],
            )
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            Order.objects.filter(
                id=self.owner_order.id,
            ).exists()
        )

    def test_checkout_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        csrf_client.login(
            username="owner",
            password="testpassword123",
        )

        orders_before = Order.objects.filter(
            owner=self.owner,
        ).count()

        response = csrf_client.post(
            reverse(
                "checkout",
                args=[self.owner_cart_item.id],
            ),
            {
                "full_name": "owner",
                "address": "Test address",
                "phone_number": "123456789",
                "size": "M",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            Order.objects.filter(
                owner=self.owner,
            ).count(),
            orders_before,
        )

        self.assertTrue(
            CartItem.objects.filter(
                id=self.owner_cart_item.id,
            ).exists()
        )

    def test_checkout_all_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        csrf_client.login(
            username="owner",
            password="testpassword123",
        )

        orders_before = Order.objects.filter(
            owner=self.owner,
        ).count()

        response = csrf_client.post(
            reverse("checkout_all"),
            {
                "full_name": "owner",
                "address": "Test address",
                "phone_number": "123456789",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertEqual(
            Order.objects.filter(
                owner=self.owner,
            ).count(),
            orders_before,
        )

        self.assertTrue(
            CartItem.objects.filter(
                id=self.owner_cart_item.id,
            ).exists()
        )
        
    def test_user_cannot_checkout_other_users_cart_item(self):
        self.client.login(
            username="other_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "checkout",
                args=[self.owner_cart_item.id],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_view_other_users_order(self):
        self.client.login(
            username="other_user",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "order_detail",
                args=[self.owner_order.id],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_other_users_order(self):
        self.client.login(
            username="other_user",
            password="testpassword123",
        )

        response = self.client.post(
            reverse(
                "delete_order",
                args=[self.owner_order.id],
            )
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            Order.objects.filter(
                id=self.owner_order.id,
            ).exists()
        )

    # -------------------------------------------------
    # HTTP method protection
    # -------------------------------------------------

    def test_get_request_cannot_delete_order(self):
        self.client.login(
            username="owner",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "delete_order",
                args=[self.owner_order.id],
            )
        )

        self.assertEqual(response.status_code, 405)

        self.assertTrue(
            Order.objects.filter(
                id=self.owner_order.id,
            ).exists()
        )

    # -------------------------------------------------
    # Legitimate access
    # -------------------------------------------------

    def test_order_owner_can_view_own_order(self):
        self.client.login(
            username="owner",
            password="testpassword123",
        )

        response = self.client.get(
            reverse(
                "order_detail",
                args=[self.owner_order.id],
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_order_owner_can_delete_own_order(self):
        self.client.login(
            username="owner",
            password="testpassword123",
        )

        response = self.client.post(
            reverse(
                "delete_order",
                args=[self.owner_order.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            Order.objects.filter(
                id=self.owner_order.id,
            ).exists()
        )