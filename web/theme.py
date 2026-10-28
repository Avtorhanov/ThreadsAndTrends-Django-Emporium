"""Оформление витрины. Выбор покупателя хранится в cookie, чтобы сервер сразу отдал атрибуты
<html> (data-theme, data-palette, data-accent, data-radius, data-text): страница рисуется в
нужном виде без мигания. Значения — только из белого списка content.look. Нет cookie —
то, что администратор выбрал для новых посетителей (панель → «Тема»)."""

from content import look

COOKIE = "theme"
LIGHT = "light"
DARK = "dark"
SYSTEM = "system"
CHOICES = [(SYSTEM, "Как в системе"), (LIGHT, "Светлая"), (DARK, "Тёмная")]
COOKIE_MAX_AGE = 60 * 60 * 24 * 365

# Cookie выбора покупателя (не httponly: site.js меняет вид без перезагрузки и пишет их сам).
LOOK_COOKIES = {"palette": "palette", "accent": "accent", "radius": "radius", "text": "text_size"}


def get_theme(request) -> str:
    """Явно выбранная тема или "" (как в системе). Нет выбора — тема по умолчанию магазина."""
    value = request.COOKIES.get(COOKIE)
    if value is None:
        value = look.shop_theme().default_mode
    return value if value in (LIGHT, DARK) else ""


def get_look(request) -> look.Look:
    return look.resolve_look(
        **{field: request.COOKIES.get(name, "") for field, name in LOOK_COOKIES.items()}
    )


def apply_theme(response, value: str):
    # «Как в системе» — тоже явный выбор: cookie хранит его, иначе подставилась бы тема магазина.
    if value in (LIGHT, DARK, SYSTEM):
        response.set_cookie(COOKIE, value, max_age=COOKIE_MAX_AGE, samesite="Lax")
    else:
        response.delete_cookie(COOKIE, samesite="Lax")
    return response


def apply_look(response, values: dict):
    """Сохранить выбор (палитра, акцент, углы, текст); недопустимое значение не пишется."""
    allowed = {
        "palette": look.shop_theme().palettes,
        "accent": tuple(look.ACCENTS),
        "radius": look.RADIUS,
        "text": look.TEXT,
    }
    for field, name in LOOK_COOKIES.items():
        value = values.get(field)
        if value in allowed[field]:
            response.set_cookie(name, value, max_age=COOKIE_MAX_AGE, samesite="Lax")
    return response


def options(request) -> dict:
    """Контекст блока «Оформление» в профиле: доступные палитры по группам, акценты, углы,
    размер текста и текущий выбор."""
    current = get_look(request)
    enabled = look.shop_theme().palettes
    groups = []
    for group, title in look.PALETTE_GROUPS.items():
        items = [p for key, p in look.PALETTES.items() if key in enabled and p["group"] == group]
        if items:
            groups.append({"title": title, "palettes": items})
    return {
        "theme_choices": CHOICES,
        "theme_value": get_theme(request) or SYSTEM,
        "look": current,
        "palette_groups": groups,
        "accents": list(look.ACCENTS.values()),
        "custom_enabled": look.CUSTOM in enabled,
        "radius_choices": list(look.RADIUS_LABELS.items()),
        "text_choices": list(look.TEXT_LABELS.items()),
    }
