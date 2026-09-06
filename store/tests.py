from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.paginator import Page
from .models import Product, Cart, CartItem, Category, SubCategory

class CartViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            password="ownerpassword123"
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="otherpassword123"
        )

        self.product = Product.objects.create(
            name="TestProduct",
            description="Test Description",
            price=10.00
        )

        self.cart = Cart.objects.create(owner=self.user)

    def create_cart_item(self, quantity=1):
        return CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=quantity,
            price=self.product.price
        )

    # -------------------------
    # ADD TO CART
    # -------------------------

    def test_update_cart_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
    
        csrf_client.login(
            username="testuser",
            password="testpassword",
        )
    
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            price=10.0,
        )
    
        response = csrf_client.post(
            reverse(
                'update_cart_item',
                args=[cart_item.id, 2],
            )
        )
    
        self.assertEqual(response.status_code, 403)
    
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)

    def test_remove_from_cart_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        csrf_client.login(
            username="testuser",
            password="testpassword",
        )

        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            price=10.0,
        )

        response = csrf_client.post(
            reverse(
                'remove_from_cart',
                args=[cart_item.id],
            )
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            CartItem.objects.filter(
                id=cart_item.id
            ).exists()
        )

    def test_add_to_cart_authenticated_user(self):
        self.client.login(
            username="owner",
            password="ownerpassword123"
        )

        response = self.client.post(
            reverse("add_to_cart", args=[self.product.id])
        )

        self.assertEqual(response.status_code, 200)

        cart_item = CartItem.objects.get(
            product=self.product,
            cart=self.cart
        )

        self.assertEqual(cart_item.quantity, 1)

    def test_add_to_cart_guest_user(self):
        response = self.client.post(
            reverse("add_to_cart", args=[self.product.id])
        )

        self.assertEqual(response.status_code, 200)

        session_cart_products = self.client.session.get(
            "cart_products",
            []
        )

        self.assertIn(
            self.product.id,
            session_cart_products
        )

    # -------------------------
    # CART VIEW
    # -------------------------

    def test_cart_view_authenticated_user(self):
        self.client.login(
            username="owner",
            password="ownerpassword123"
        )

        response = self.client.get(reverse("cart"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/cart.html")

    def test_cart_view_guest_user_redirected_to_login(self):
        response = self.client.get(reverse("cart"))

        self.assertEqual(response.status_code, 302)

    # -------------------------
    # UPDATE CART SECURITY
    # -------------------------

    def test_cart_owner_can_update_cart_item(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            price=10.0,
        )
    
        self.client.login(
            username="owner",
            password="ownerpassword123",
        )
    
        response = self.client.post(
            reverse('update_cart_item', args=[cart_item.id,     2])
        )
    
        self.assertEqual(response.status_code, 200)
    
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)

    def test_anonymous_user_cannot_update_cart_item(self):
        cart_item = self.create_cart_item()

        response = self.client.post(
            reverse(
                "update_cart_item",
                args=[cart_item.id, 2]
            )
        )

        self.assertIn(
            response.status_code,
            [302, 403]
        )

        cart_item.refresh_from_db()

        self.assertEqual(
            cart_item.quantity,
            1
        )

    def test_other_user_cannot_update_cart_item(self):
        other_user = User.objects.create_user(
            username="otheruser",
            password="otherpassword",
        )

        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            price=10.0,
        )

        self.client.login(
            username="otheruser",
            password="otherpassword",
        )

        response = self.client.post(
            reverse('update_cart_item', args=[cart_item.id,     2])
        )

        self.assertEqual(response.status_code, 404)

        cart_item.refresh_from_db()

        self.assertEqual(cart_item.quantity, 1)

    # -------------------------
    # REMOVE CART SECURITY
    # -------------------------

    def test_cart_owner_can_remove_cart_item(self):
        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            price=10.0,
        )

        self.client.login(
            username="owner",
            password="ownerpassword123",
        )

        response = self.client.post(
            reverse('remove_from_cart', args=[cart_item.id])
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            CartItem.objects.filter(id=cart_item.id).exists()
        )

    def test_add_to_cart_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(
            reverse('add_to_cart', args=[self.product.id])
        )

        self.assertEqual(response.status_code, 403)

    def test_get_request_cannot_add_to_cart(self):
        response = self.client.get(
            reverse('add_to_cart', args=[self.product.id])
        )

        self.assertEqual(response.status_code, 405)

    def test_anonymous_user_cannot_remove_cart_item(self):
        cart_item = self.create_cart_item()

        response = self.client.post(
            reverse(
                "remove_from_cart",
                args=[cart_item.id]
            )
        )

        self.assertIn(
            response.status_code,
            [302, 403]
        )

        self.assertTrue(
            CartItem.objects.filter(
                id=cart_item.id
            ).exists()
        )

    def test_other_user_cannot_remove_cart_item(self):
        other_user = User.objects.create_user(
            username="otheruser",
            password="otherpassword",
        )

        cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1,
            price=10.0,
        )

        self.client.login(
            username="otheruser",
            password="otherpassword",
        )

        response = self.client.post(
            reverse('remove_from_cart', args=[cart_item.id])
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            CartItem.objects.filter(id=cart_item.id).exists()
        )

    def test_guest_cart_is_merged_into_user_cart_after_login(self):
        # Гость добавляет товар
        response = self.client.post(
            reverse("add_to_cart", args=[self.product.id])
        )
        self.assertEqual(response.status_code, 200)

        # Проверяем, что товар появился в session
        self.assertIn(
            self.product.id,
            self.client.session.get("cart_products", [])
        )

        # Гость авторизуется
        self.client.login(
            username="owner",
            password="ownerpassword123",
        )

        # Проверяем, что товар перенесён в корзину  пользователя
        cart_item = CartItem.objects.get(
            cart__owner=self.user,
            product=self.product,
        )

        self.assertEqual(cart_item.quantity, 1)

        # Проверяем очистку guest session
        self.assertNotIn(
            self.product.id,
            self.client.session.get("cart_products", [])
        )


def test_guest_cart_merge_increases_existing_item_quantity(self):
    # У пользователя уже есть этот товар
    CartItem.objects.create(
        cart=self.cart,
        product=self.product,
        quantity=2,
        price=self.product.price,
    )

    # Гость добавляет такой же товар
    self.client.post(
        reverse("add_to_cart", args=[self.product.id])
    )

    # Авторизация
    self.client.login(
        username="owner",
        password="ownerpassword123",
    )

    # После merge количество должно увеличиться
    cart_item = CartItem.objects.get(
        cart__owner=self.user,
        product=self.product,
    )

    self.assertEqual(cart_item.quantity, 3)    
 
class ModelsTestCase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="TestCategory")
        self.subcategory = SubCategory.objects.create(name="TestSubCategory", category=self.category)
        self.product = Product.objects.create(name="TestProduct", description="Test Description", price=10.0, category=self.category, subcategory=self.subcategory)
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.cart = Cart.objects.create(owner=self.user)

    def test_category_creation(self):
        category = Category.objects.get(name="TestCategory")
        self.assertEqual(category.name, "TestCategory")

    def test_subcategory_creation(self):
        subcategory = SubCategory.objects.get(name="TestSubCategory")
        self.assertEqual(subcategory.category, self.category)

    def test_product_creation(self):
        product = Product.objects.get(name="TestProduct")
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.subcategory, self.subcategory)

class AllProductsViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()  # Создаем экземпляр тестового клиента
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.category = Category.objects.create(name="Test Category")
        for i in range(15):
            Product.objects.create(name=f"Product {i}", description=f"Description {i}", price=10.0, category=self.category)

    def test_all_products_view(self):
        url = reverse('all-products')
        response = self.client.get(url)  # Используем тестовый клиент для выполнения запроса
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/products.html')
        self.assertTrue('page_obj' in response.context)
        self.assertTrue('categories' in response.context)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue('start_page' in response.context)
        self.assertTrue('end_page' in response.context)
        self.assertIsInstance(response.context['page_obj'], Page)
        self.assertEqual(response.context['categories'].count(), 1)  # One category is created in setup
        self.assertTrue(response.context['is_paginated'])
        self.assertTrue(response.context['start_page'] >= 1)
        self.assertTrue(response.context['end_page'] <= 3)  # Assuming paginator has 3 pages for 15 products

class SearchProductsViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
    def test_search_products_view(self):
        response = self.client.get(reverse('search_products'), {'q': 'lacoste'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/search_results.html')
        self.assertIn('products', response.context)

