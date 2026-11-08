"""Секретные ссылки на гостевые заказы в сессии: при входе заказы привязываются к аккаунту."""

SESSION_KEY = "guest_orders"
MAX_LINKS = 20


def remember(request, token: str) -> None:
    tokens = [t for t in request.session.get(SESSION_KEY, []) if t != token]
    request.session[SESSION_KEY] = [*tokens, token][-MAX_LINKS:]


def take(request) -> list[str]:
    return request.session.pop(SESSION_KEY, [])
