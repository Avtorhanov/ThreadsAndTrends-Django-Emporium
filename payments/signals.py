from django.dispatch import receiver

from orders.models import Order
from orders.signals import order_cancelled

from . import services


@receiver(order_cancelled, sender=Order)
def refund_paid_order(sender, order, was_paid, **kwargs):
    # Внутри транзакции отмены: возврат создаётся вместе с отменой, отправляется после commit.
    if was_paid:
        services.refund_cancelled_order(order)
