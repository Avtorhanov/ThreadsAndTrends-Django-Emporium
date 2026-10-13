from django_tasks import task

from . import services


@task()
def execute_refund(refund_id: int) -> None:
    """Отправка возврата провайдеру после commit отмены (сбой сети — повтор в sync_pending)."""
    services.execute_refund(refund_id)


@task()
def sync_pending() -> None:
    """Периодическая сверка зависших платежей и возвратов (settings.PERIODIC_TASKS)."""
    services.sync_stale()


@task()
def cancel_unpaid_orders() -> None:
    """Периодическая автоотмена онлайн-заказов, не оплаченных за ORDERS_UNPAID_TIMEOUT_MINUTES."""
    services.cancel_unpaid_orders()
