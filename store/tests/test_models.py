import pytest

from store.models import Product

from .factories import make_category, make_product

pytestmark = pytest.mark.django_db


def test_category_tree_and_product():
    category = make_category(name="TestCategory")
    child = make_category(name="TestSubCategory", parent=category)
    make_product(name="TestProduct", category=child)

    assert list(category.children.all()) == [child]
    assert str(child) == "TestCategory / TestSubCategory"
    product = Product.objects.get(name="TestProduct")
    assert product.category == child
    assert product.in_stock
