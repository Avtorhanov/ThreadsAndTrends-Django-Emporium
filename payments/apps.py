from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payments"
    verbose_name = "Платежи"

    def ready(self):
        import payments.checks  # noqa: F401  регистрирует system checks
        import payments.signals  # noqa: F401  регистрирует обработчики сигналов
