"""Тема витрины. Выбор хранится в cookie, чтобы сервер сразу отдал `data-theme` на <html>:
страница рисуется в нужной теме без мигания. Нет cookie — тема системы (prefers-color-scheme)."""

COOKIE = "theme"
LIGHT = "light"
DARK = "dark"
SYSTEM = "system"
CHOICES = [(SYSTEM, "Как в системе"), (LIGHT, "Светлая"), (DARK, "Тёмная")]
COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def get_theme(request) -> str:
    """Явно выбранная тема или "" (как в системе)."""
    value = request.COOKIES.get(COOKIE, "")
    return value if value in (LIGHT, DARK) else ""


def apply_theme(response, value: str):
    if value in (LIGHT, DARK):
        # Не httponly: переключатель в шапке меняет тему без перезагрузки и сам пишет cookie.
        response.set_cookie(COOKIE, value, max_age=COOKIE_MAX_AGE, samesite="Lax")
    else:
        response.delete_cookie(COOKIE, samesite="Lax")
    return response
