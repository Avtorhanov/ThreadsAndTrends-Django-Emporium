from django.contrib.auth import get_user_model
from django.core.paginator import Page
from django.test import Client, TestCase
from django.urls import reverse

from store.models import Product

from .factories import make_category, make_product

User = get_user_model()


class ModelsTestCase(TestCase):
    def setUp(self):
        self.category = make_category(name="TestCategory")
        self.child = make_category(name="TestSubCategory", parent=self.category)
        self.product = make_product(name="TestProduct", category=self.child)

    def test_category_tree(self):
        self.assertEqual(list(self.category.children.all()), [self.child])
        self.assertEqual(str(self.child), "TestCategory / TestSubCategory")

    def test_product_creation(self):
        product = Product.objects.get(name="TestProduct")
        self.assertEqual(product.category, self.child)
        self.assertTrue(product.in_stock)


class AllProductsViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()  # Создаем экземпляр тестового клиента
        self.user = User.objects.create_user(email="testuser@example.com", password="testpassword")
        self.category = make_category(name="Test Category")
        for i in range(15):
            make_product(name=f"Product {i}", category=self.category)

    def test_all_products_view(self):
        url = reverse("all-products")
        response = self.client.get(url)  # Используем тестовый клиент для выполнения запроса
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "store/products.html")
        self.assertTrue("page_obj" in response.context)
        self.assertTrue("categories" in response.context)
        self.assertTrue("is_paginated" in response.context)
        self.assertTrue("start_page" in response.context)
        self.assertTrue("end_page" in response.context)
        self.assertIsInstance(response.context["page_obj"], Page)
        self.assertEqual(
            response.context["categories"].count(), 1
        )  # One category is created in setup
        self.assertTrue(response.context["is_paginated"])
        self.assertTrue(response.context["start_page"] >= 1)
        self.assertTrue(
            response.context["end_page"] <= 3
        )  # Assuming paginator has 3 pages for 15 products


class SearchProductsViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_search_products_view(self):
        response = self.client.get(reverse("search_products"), {"q": "lacoste"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main/search_results.html")
        self.assertIn("products", response.context)
