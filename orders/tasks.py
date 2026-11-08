from django_tasks import task

from .services import agreement


@task()
def cancel_stale_agreements() -> None:
    """Периодическая автоотмена заказов «по согласованию», не подтверждённых продавцом."""
    agreement.cancel_stale()
