from django.apps import AppConfig


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "content"
    verbose_name = "Статьи и контакты"

    def ready(self):
        from . import checks  # noqa: F401  content.W001 — неверные контакты в .env
