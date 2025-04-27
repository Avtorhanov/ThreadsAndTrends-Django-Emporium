from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.paginator import Page
from .models import Product, Cart, CartItem, Category, SubCategory

class CartViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.product = Product.objects.create(name="TestProduct", description="Test Description", price=10.0)
        self.cart = Cart.objects.create(owner=self.user)

    def test_add_to_cart_authenticated_user(self):
        self.client.login(username="testuser", password="testpassword")
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        cart_item = CartItem.objects.get(product=self.product, cart=self.cart)
        self.assertEqual(cart_item.quantity, 1)

    def test_add_to_cart_guest_user(self):
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        session_cart_products = self.client.session.get('cart_products', [])
        self.assertIn(str(self.product.id), map(str, session_cart_products))

    def test_cart_view_authenticated_user(self):
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'orders/cart.html')

    def test_cart_view_guest_user(self):
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 302)  # Redirects to login if not authenticated

    def test_update_cart(self):
        cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1, price=10.0)
        response = self.client.post(reverse('update_cart_item', args=[cart_item.id, 2]))
        self.assertEqual(response.status_code, 200)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)

    def test_remove_from_cart(self):
        cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1, price=10.0)
        response = self.client.post(reverse('remove_from_cart', args=[cart_item.id]))
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(CartItem.DoesNotExist):
            cart_item.refresh_from_db()

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

