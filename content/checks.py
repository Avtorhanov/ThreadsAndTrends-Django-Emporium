from django.core.checks import Warning, register

from .contacts import invalid_settings


@register()
def contacts_are_valid(app_configs, **kwargs):
    return [
        Warning(
            f"{name}: значение не распознано — канал не показывается на вкладке «Контакты».",
            hint="WhatsApp и телефон — номер (+7 900 123-45-67), Telegram — @имя или "
            "ссылка t.me/имя, ВКонтакте — короткое имя или ссылка vk.com/имя.",
            id="content.W001",
        )
        for name in invalid_settings()
    ]
