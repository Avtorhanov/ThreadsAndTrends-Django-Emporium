from django.core.exceptions import ValidationError
from django.dispatch import receiver

from accounts.signals import account_deleted, account_deleting
from orders.models import Order

# Статусы, при которых заказ ещё исполняется. Пересматриваются в сессии 5 (state machine).
ACTIVE_STATUSES = ["В обработке", "В пути"]


@receiver(account_deleting)
def forbid_deletion_with_active_orders(sender, user, **kwargs):
    if Order.objects.filter(owner=user, status__in=ACTIVE_STATUSES).exists():
        raise ValidationError(
            "Нельзя удалить аккаунт, пока есть незавершённые заказы. "
            "Дождитесь доставки или отмените их."
        )


@receiver(account_deleted)
def anonymize_orders(sender, user, **kwargs):
    # Заказ остаётся для учёта, персональные данные получателя стираются.
    Order.objects.filter(owner=user).update(full_name="", phone_number="", address="")
