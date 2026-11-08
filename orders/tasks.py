from django_tasks import task

from .services import agreement, guest


@task()
def cancel_stale_agreements() -> None:
    """Периодическая автоотмена заказов «по согласованию», не подтверждённых продавцом."""
    agreement.cancel_stale()


@task()
def anonymize_guest_orders() -> None:
    """Стирает получателя в гостевых заказах, завершённых давно (срок — orders.services.guest)."""
    guest.anonymize_old()
