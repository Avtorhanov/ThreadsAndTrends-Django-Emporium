from django.core.exceptions import ValidationError
from django.dispatch import Signal, receiver

from accounts.signals import account_deleted, account_deleting
from orders.models import Order

# Заказ отменён (sender=Order, order=<Order>, was_paid=<bool>). Отправляется внутри транзакции
# отмены после возврата остатков. was_paid=True — заказ был оплачен онлайн: платежи
# (сессия 6) оформляют по нему возврат денег.
order_cancelled = Signal()


@receiver(account_deleting)
def forbid_deletion_with_unfinished_orders(sender, user, **kwargs):
    if Order.objects.filter(owner=user).unfinished().exists():
        raise ValidationError(
            "Нельзя удалить аккаунт, пока есть незавершённые заказы. "
            "Дождитесь получения или отмените их."
        )


@receiver(account_deleted)
def anonymize_orders(sender, user, **kwargs):
    # Заказ остаётся для учёта, персональные данные получателя стираются.
    Order.objects.filter(owner=user).update(
        recipient_name="", recipient_phone="", delivery_address="", comment=""
    )
