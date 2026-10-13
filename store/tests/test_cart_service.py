import pytest
from django.core.exceptions import ValidationError
from django.http import Http404
from django.utils import timezone

from store.models import Cart, CartItem, Category, Product, ProductVariant
from store.services import cart as cart_service
from store.services.cart import LineInput, LineStatus

from .factories import make_category, make_product

pytestmark = pytest.mark.django_db


def variant_of(product, size=""):
    return product.variants.get(size=size)


def codes(error: ValidationError) -> set[str]:
    return {e.code for e in error.error_list}


@pytest.fixture
def shirt():
    return make_product(name="Футболка", price_kopecks=1_500_00, stock=5, sizes=("S", "M"))


@pytest.fixture
def cap():
    return make_product(name="Кепка", price_kopecks=990_00, stock=20)


# --- Добавление и количество ---


def test_add_creates_cart_and_item_with_current_price(customer, shirt):
    summary = cart_service.add(customer, variant_of(shirt, "M").pk, 2)

    item = CartItem.objects.get(cart__owner=customer)
    assert (item.variant.size, item.quantity, item.seen_price_kopecks) == ("M", 2, 1_500_00)
    assert summary.total_kopecks == 3_000_00
    assert summary.items_count == 2
    assert summary.can_checkout
    [line] = summary.lines
    assert (line.id, line.status, line.max_quantity) == (item.pk, LineStatus.OK, 5)


def test_add_same_variant_increments_quantity(customer, shirt):
    variant = variant_of(shirt, "S")
    cart_service.add(customer, variant.pk)
    summary = cart_service.add(customer, variant.pk, 2)

    assert [line.quantity for line in summary.lines] == [3]
    assert CartItem.objects.count() == 1


def test_add_is_limited_by_stock(customer, shirt):
    variant = variant_of(shirt, "S")
    cart_service.add(customer, variant.pk, 4)

    with pytest.raises(ValidationError) as error:
        cart_service.add(customer, variant.pk, 2)

    assert codes(error.value) == {"quantity_limit"}
    assert error.value.messages == ["Можно добавить не больше 5 шт. В корзине уже 4."]
    assert CartItem.objects.get().quantity == 4


def test_add_is_limited_by_max_quantity_setting(customer, cap, settings):
    settings.CART_MAX_QUANTITY = 3  # остаток кепок — 20

    with pytest.raises(ValidationError) as error:
        cart_service.add(customer, variant_of(cap).pk, 4)

    assert codes(error.value) == {"quantity_limit"}
    assert cart_service.add(customer, variant_of(cap).pk, 3).lines[0].max_quantity == 3


def test_add_respects_cart_items_limit(customer, settings):
    settings.CART_MAX_ITEMS = 2
    products = [make_product() for _ in range(3)]
    cart_service.add(customer, variant_of(products[0]).pk)
    cart_service.add(customer, variant_of(products[1]).pk)

    with pytest.raises(ValidationError) as error:
        cart_service.add(customer, variant_of(products[2]).pk)
    assert codes(error.value) == {"cart_full"}
    # Увеличить количество уже добавленной позиции можно.
    cart_service.add(customer, variant_of(products[0]).pk)


def deactivate(product, variant):
    Product.objects.filter(pk=product.pk).update(is_active=False)


def delete_product(product, variant):
    Product.objects.filter(pk=product.pk).update(deleted_at=timezone.now())


def delete_variant(product, variant):
    ProductVariant.all_objects.filter(pk=variant.pk).update(deleted_at=timezone.now())


def hide_category(product, variant):
    Category.objects.filter(pk=product.category_id).update(is_active=False)


def hide_parent_category(product, variant):
    Category.objects.filter(pk=product.category.parent_id).update(is_active=False)


@pytest.mark.parametrize(
    "make_unavailable",
    [deactivate, delete_product, delete_variant, hide_category, hide_parent_category],
)
def test_unavailable_variant_cannot_be_added_and_is_marked_in_cart(customer, make_unavailable):
    product = make_product(category=make_category(parent=make_category()), price_kopecks=100_00)
    variant = variant_of(product)
    cart_service.add(customer, variant.pk, 2)

    make_unavailable(product, variant)

    with pytest.raises(ValidationError) as error:
        cart_service.add(customer, variant.pk)
    assert codes(error.value) == {"unavailable"}

    summary = cart_service.get_summary(customer)
    [line] = summary.lines
    assert (line.status, line.max_quantity, line.line_total_kopecks) == (
        LineStatus.UNAVAILABLE,
        0,
        0,
    )
    assert line.product == product  # название по-прежнему можно показать
    assert summary.total_kopecks == 0
    assert not summary.can_checkout


def test_out_of_stock_variant_cannot_be_added(customer):
    product = make_product(stock=0)
    with pytest.raises(ValidationError) as error:
        cart_service.add(customer, variant_of(product).pk)
    assert codes(error.value) == {"out_of_stock"}


def test_nonexistent_variant_cannot_be_added(customer):
    with pytest.raises(ValidationError) as error:
        cart_service.add(customer, 999_999)
    assert codes(error.value) == {"unavailable"}


def test_set_quantity_validates_range(customer, shirt):
    summary = cart_service.add(customer, variant_of(shirt, "S").pk)
    item_id = summary.lines[0].id

    for bad in (0, 6):
        with pytest.raises(ValidationError) as error:
            cart_service.set_quantity(customer, item_id, bad)
        assert codes(error.value) == {"quantity_limit"}

    assert cart_service.set_quantity(customer, item_id, 5).lines[0].quantity == 5


def test_set_quantity_of_unavailable_item_is_rejected(customer, shirt):
    variant = variant_of(shirt, "S")
    item_id = cart_service.add(customer, variant.pk).lines[0].id
    variant.stock = 0
    variant.save()

    with pytest.raises(ValidationError) as error:
        cart_service.set_quantity(customer, item_id, 1)
    assert codes(error.value) == {"out_of_stock"}


def test_foreign_cart_item_is_not_found(customer, staff, shirt):
    item_id = cart_service.add(customer, variant_of(shirt, "S").pk).lines[0].id

    with pytest.raises(Http404):
        cart_service.set_quantity(staff, item_id, 2)
    with pytest.raises(Http404):
        cart_service.remove(staff, item_id)
    assert CartItem.objects.get(pk=item_id).quantity == 1


def test_remove(customer, shirt, cap):
    cart_service.add(customer, variant_of(shirt, "S").pk)
    summary = cart_service.add(customer, variant_of(cap).pk)

    summary = cart_service.remove(customer, summary.lines[0].id)

    assert [line.product for line in summary.lines] == [cap]


# --- Состояние корзины ---


def test_get_summary_does_not_create_cart(customer):
    summary = cart_service.get_summary(customer)
    assert (summary.lines, summary.total_kopecks, summary.can_checkout) == ([], 0, False)
    assert not Cart.objects.exists()


def test_stock_drop_marks_line_and_blocks_checkout(customer, shirt, cap):
    variant = variant_of(shirt, "S")
    cart_service.add(customer, variant.pk, 4)
    cart_service.add(customer, variant_of(cap).pk, 1)
    variant.stock = 2
    variant.save()

    summary = cart_service.get_summary(customer)

    shirt_line, cap_line = summary.lines
    assert (shirt_line.status, shirt_line.max_quantity, shirt_line.quantity) == (
        LineStatus.EXCEEDS_STOCK,
        2,
        4,  # чтение корзину не меняет
    )
    assert summary.total_kopecks == cap_line.line_total_kopecks == 990_00
    assert summary.has_problems and not summary.can_checkout

    variant.stock = 0
    variant.save()
    assert cart_service.get_summary(customer).lines[0].status == LineStatus.OUT_OF_STOCK


def test_total_uses_current_price_and_warns_until_acknowledged(customer, shirt):
    cart_service.add(customer, variant_of(shirt, "S").pk, 2)
    shirt.price_kopecks = 1_200_00
    shirt.save()

    summary = cart_service.get_summary(customer)
    [line] = summary.lines
    assert summary.total_kopecks == 2_400_00
    assert (line.price_changed, line.seen_price_kopecks, line.unit_price_kopecks) == (
        True,
        1_500_00,
        1_200_00,
    )
    assert summary.has_price_changes
    assert summary.can_checkout  # изменение цены не мешает оформлению

    summary = cart_service.ack_prices(customer)
    assert not summary.has_price_changes
    assert summary.lines[0].seen_price_kopecks == 1_200_00


# --- Гостевая корзина ---


def test_quote_matches_saved_cart_and_writes_nothing(customer, shirt, cap):
    lines = [
        LineInput(variant_of(shirt, "M").pk, 2, 1_500_00),
        LineInput(variant_of(cap).pk, 3, 990_00),
    ]
    quote = cart_service.quote(lines)
    assert not Cart.objects.exists()

    for line in lines:
        cart_service.add(customer, line.variant_id, line.quantity)
    saved = cart_service.get_summary(customer)

    assert quote.total_kopecks == saved.total_kopecks == 2 * 1_500_00 + 3 * 990_00
    assert [(x.variant_id, x.quantity, x.status) for x in quote.lines] == [
        (x.variant_id, x.quantity, x.status) for x in saved.lines
    ]
    assert all(line.id is None for line in quote.lines)


def test_quote_marks_unknown_variant_and_merges_duplicates(shirt):
    variant = variant_of(shirt, "S")
    summary = cart_service.quote(
        [LineInput(variant.pk, 1, 1_000_00), LineInput(999_999, 1), LineInput(variant.pk, 2)]
    )

    first, unknown = summary.lines
    assert (first.quantity, first.status, first.price_changed) == (3, LineStatus.OK, True)
    assert (unknown.status, unknown.product, unknown.unit_price_kopecks) == (
        LineStatus.UNAVAILABLE,
        None,
        None,
    )
    assert not unknown.price_changed
    assert summary.total_kopecks == 3 * 1_500_00


def test_quote_rejects_too_many_lines(settings):
    settings.CART_MAX_ITEMS = 1
    products = [make_product(), make_product()]
    with pytest.raises(ValidationError) as error:
        cart_service.quote([LineInput(variant_of(p).pk, 1) for p in products])
    assert codes(error.value) == {"cart_full"}


# --- Слияние при входе ---


def test_merge_into_empty_account_keeps_guest_seen_price(customer, shirt):
    variant = variant_of(shirt, "M")
    result = cart_service.merge(customer, [LineInput(variant.pk, 2, 1_700_00)])

    assert result.notices == []
    [line] = result.summary.lines
    assert (line.quantity, line.seen_price_kopecks, line.price_changed) == (2, 1_700_00, True)


def test_merge_sums_quantities_and_limits_by_stock(customer, shirt, cap):
    shirt_s = variant_of(shirt, "S")
    cart_service.add(customer, shirt_s.pk, 3)
    cart_service.add(customer, variant_of(cap).pk, 1)

    result = cart_service.merge(
        customer,
        [
            LineInput(shirt_s.pk, 4, 1),  # 3 + 4 > остатка 5
            LineInput(variant_of(cap).pk, 2, 1),
            LineInput(variant_of(shirt, "M").pk, 7),  # новая позиция больше остатка
        ],
    )

    quantities = {line.variant_id: line.quantity for line in result.summary.lines}
    assert quantities == {shirt_s.pk: 5, variant_of(cap).pk: 3, variant_of(shirt, "M").pk: 5}
    assert {(n.variant_id, n.reason) for n in result.notices} == {
        (shirt_s.pk, "quantity_limited"),
        (variant_of(shirt, "M").pk, "quantity_limited"),
    }
    # У уже лежавших позиций «увиденная» цена не меняется.
    assert {line.seen_price_kopecks for line in result.summary.lines} == {1_500_00, 990_00}


def test_merge_skips_unavailable_unknown_and_out_of_stock(customer):
    hidden = make_product(is_active=False)
    empty = make_product(stock=0)
    ok = make_product(price_kopecks=10_00)

    result = cart_service.merge(
        customer,
        [
            LineInput(variant_of(hidden).pk, 1),
            LineInput(999_999, 1),
            LineInput(variant_of(empty).pk, 1),
            LineInput(variant_of(ok).pk, 1),
        ],
    )

    assert [line.product for line in result.summary.lines] == [ok]
    assert {(n.variant_id, n.reason) for n in result.notices} == {
        (variant_of(hidden).pk, "unavailable"),
        (999_999, "unavailable"),
        (variant_of(empty).pk, "out_of_stock"),
    }


def test_merge_respects_cart_items_limit(customer, settings):
    settings.CART_MAX_ITEMS = 1
    first, second = make_product(), make_product()

    result = cart_service.merge(
        customer, [LineInput(variant_of(first).pk, 1), LineInput(variant_of(second).pk, 1)]
    )

    assert [line.product for line in result.summary.lines] == [first]
    assert [(n.variant_id, n.reason) for n in result.notices] == [
        (variant_of(second).pk, "cart_full")
    ]


def test_merge_does_not_reduce_existing_quantity(customer, shirt):
    variant = variant_of(shirt, "S")
    cart_service.add(customer, variant.pk, 4)
    variant.stock = 2
    variant.save()

    result = cart_service.merge(customer, [LineInput(variant.pk, 1)])

    # Позиция остаётся как была (exceeds_stock) — покупатель сам выберет количество.
    assert result.summary.lines[0].quantity == 4
    assert result.summary.lines[0].status == LineStatus.EXCEEDS_STOCK
