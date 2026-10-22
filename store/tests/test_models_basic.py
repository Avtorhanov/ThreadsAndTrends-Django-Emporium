from django.test import TestCase

from store.models import Product

from .factories import make_category, make_product


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
