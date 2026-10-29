from django.urls import reverse

from orders.models import OrderStatus
from orders.tests.factories import make_order
from store.models import ProductView
from store.services import cart as cart_service

from .conftest import image_file


def test_product_page_records_view_and_shows_similar(customer_client, customer, shop):
    html = customer_client.get(reverse("web:product", args=["futbolka-belaya"])).content.decode()
    assert ProductView.objects.filter(user=customer, product=shop["shirt"]).exists()
    similar = html.split('id="similar-title"')[1]
    assert "/product/hudi/" in similar and "/product/kepka/" in similar
    assert "/product/skrytyy/" not in similar and "/product/futbolka-belaya/" not in similar


def test_guest_view_is_not_recorded(client, shop):
    client.get(reverse("web:product", args=["futbolka-belaya"]))
    assert not ProductView.objects.exists()


def test_profile_shows_purchases_cart_and_viewed(customer_client, customer, shop):
    delivered = make_order(customer, shop["cap"], status=OrderStatus.DELIVERED)
    make_order(customer, shop["cap"], status=OrderStatus.CANCELLED)
    cart_service.add(customer, shop["shirt"].variants.first().pk, 2)
    customer_client.get(reverse("web:product", args=["kepka"]))
    html = customer_client.get(reverse("web:profile")).content.decode()
    purchases = html.split('id="me-purchases"')[1].split("</section>")[0]
    assert delivered.number in purchases
    assert "2 шт." in html.split('id="me-cart"')[1]
    assert "/product/kepka/" in html.split('id="me-viewed"')[1]


def test_viewed_clear(customer_client, customer, shop):
    customer_client.get(reverse("web:product", args=["kepka"]))
    response = customer_client.post(reverse("web:viewed_clear"))
    assert response.status_code == 302
    assert not ProductView.objects.filter(user=customer).exists()


def test_avatar_upload_and_remove(customer_client, customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = customer_client.post(reverse("web:avatar"), {"avatar": image_file()})
    assert response.status_code == 302
    customer.refresh_from_db()
    assert customer.avatar
    assert customer.avatar.url in customer_client.get(reverse("web:profile")).content.decode()
    customer_client.post(reverse("web:avatar"), {"remove": "1"})
    customer.refresh_from_db()
    assert not customer.avatar


def test_look_page_for_guest(client, db):
    html = client.get(reverse("web:profile_look")).content.decode()
    assert 'name="palette"' in html and 'name="radius"' in html
    assert reverse("web:profile_look") in client.get(reverse("web:profile")).content.decode()


def test_profile_data_requires_login(client, db):
    response = client.get(reverse("web:profile_data"))
    assert response.status_code == 302 and response["Location"].startswith(reverse("web:login"))
