import pytest
from django.core import mail
from django.core.exceptions import ValidationError

from orders.models import ChangedBy, DeliveryMethod, OrderStatus, PaymentMethod
from orders.services import status as status_service
from orders.signals import order_cancelled
from store.models import ProductVariant

from .factories import make_order

pytestmark = pytest.mark.django_db

S = OrderStatus


@pytest.fixture
def cancelled_events():
    events = []

    def receiver(sender, order, was_paid, **kwargs):
        events.append((order.number, was_paid))

    order_cancelled.connect(receiver)
    yield events
    order_cancelled.disconnect(receiver)


def variant_stock(order):
    item = order.items.get()
    return ProductVariant.all_objects.get(pk=item.variant_id).stock


@pytest.mark.parametrize(
    ("status", "delivery", "admin_targets", "customer_targets"),
    [
        (S.AWAITING_PAYMENT, DeliveryMethod.COURIER, [S.CANCELLED], [S.CANCELLED]),
        (S.CONFIRMED, DeliveryMethod.COURIER, [S.ASSEMBLED, S.CANCELLED], [S.CANCELLED]),
        (S.PAID, DeliveryMethod.COURIER, [S.ASSEMBLED, S.CANCELLED], [S.CANCELLED]),
        (S.ASSEMBLED, DeliveryMethod.COURIER, [S.SHIPPED, S.CANCELLED], [S.CANCELLED]),
        (S.ASSEMBLED, DeliveryMethod.PICKUP, [S.READY_FOR_PICKUP, S.CANCELLED], [S.CANCELLED]),
        (S.SHIPPED, DeliveryMethod.COURIER, [S.DELIVERED], []),
        (S.READY_FOR_PICKUP, DeliveryMethod.PICKUP, [S.DELIVERED, S.CANCELLED], []),
        (S.DELIVERED, DeliveryMethod.COURIER, [], []),
        (S.CANCELLED, DeliveryMethod.COURIER, [], []),
    ],
)
def test_transitions_by_role(customer, status, delivery, admin_targets, customer_targets):
    order = make_order(customer, status=status, delivery_method=delivery)
    assert status_service.allowed_transitions(order, ChangedBy.ADMIN) == admin_targets
    assert status_service.allowed_transitions(order, ChangedBy.CUSTOMER) == customer_targets


def test_customer_cancel_returns_stock_and_logs(customer, cancelled_events):
    order = make_order(customer, quantity=2)
    before = variant_stock(order)

    status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=customer)

    order.refresh_from_db()
    assert order.status == S.CANCELLED
    assert variant_stock(order) == before + 2
    last = order.status_changes.last()
    assert (last.from_status, last.to_status, last.changed_by, last.actor_id) == (
        S.CONFIRMED,
        S.CANCELLED,
        ChangedBy.CUSTOMER,
        customer.pk,
    )
    assert cancelled_events == [(order.number, False)]


def test_repeated_cancel_is_noop(customer, cancelled_events):
    order = make_order(customer)
    status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=customer)
    stock_after_cancel = variant_stock(order)

    status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=customer)

    assert variant_stock(order) == stock_after_cancel
    assert order.status_changes.count() == 2
    assert len(cancelled_events) == 1


def test_customer_cannot_cancel_shipped_order(customer):
    order = make_order(customer, status=S.SHIPPED)
    with pytest.raises(ValidationError) as exc:
        status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=customer)
    assert exc.value.error_list[0].code == "invalid_transition"
    order.refresh_from_db()
    assert order.status == S.SHIPPED


def test_admin_cannot_mark_paid_but_system_can(customer, staff):
    order = make_order(customer, status=S.AWAITING_PAYMENT, payment_method=PaymentMethod.ONLINE)
    with pytest.raises(ValidationError):
        status_service.transition(order, S.PAID, by=ChangedBy.ADMIN, actor=staff)

    status_service.mark_paid(order)
    status_service.mark_paid(order)  # повторное подтверждение провайдера ничего не меняет

    order.refresh_from_db()
    assert order.status == S.PAID
    assert order.status_changes.filter(to_status=S.PAID, changed_by=ChangedBy.SYSTEM).count() == 1


def test_cancel_after_payment_reports_paid(customer, staff, cancelled_events):
    order = make_order(customer, status=S.AWAITING_PAYMENT, payment_method=PaymentMethod.ONLINE)
    status_service.mark_paid(order)
    status_service.transition(order, S.ASSEMBLED, by=ChangedBy.ADMIN, actor=staff)

    status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=customer)

    assert cancelled_events == [(order.number, True)]


def test_delivery_specific_statuses(customer, staff):
    courier = make_order(customer, status=S.ASSEMBLED)
    with pytest.raises(ValidationError):
        status_service.transition(courier, S.READY_FOR_PICKUP, by=ChangedBy.ADMIN, actor=staff)
    status_service.transition(courier, S.SHIPPED, by=ChangedBy.ADMIN, actor=staff)
    status_service.transition(courier, S.DELIVERED, by=ChangedBy.ADMIN, actor=staff)
    courier.refresh_from_db()
    assert courier.status == S.DELIVERED

    pickup = make_order(customer, status=S.ASSEMBLED, delivery_method=DeliveryMethod.PICKUP)
    with pytest.raises(ValidationError):
        status_service.transition(pickup, S.SHIPPED, by=ChangedBy.ADMIN, actor=staff)


def test_final_status_cannot_change(customer, staff):
    order = make_order(customer, status=S.DELIVERED)
    with pytest.raises(ValidationError):
        status_service.cancel(order, by=ChangedBy.ADMIN, actor=staff)


def test_status_change_sends_email(customer, staff, django_capture_on_commit_callbacks):
    order = make_order(customer)
    with django_capture_on_commit_callbacks(execute=True):
        status_service.transition(order, S.ASSEMBLED, by=ChangedBy.ADMIN, actor=staff)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [customer.email]
    assert "собран" in mail.outbox[0].subject
