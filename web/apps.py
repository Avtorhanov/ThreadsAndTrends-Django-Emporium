from django.apps import AppConfig


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "web"
    verbose_name = "Веб-витрина"

    def ready(self):
        import web.signals  # noqa: F401  сброс кэша сеток каталога
