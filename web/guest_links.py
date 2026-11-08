"""Заказы, оформленные в этой сессии без аккаунта: при входе привязываются к нему.
Хранятся хеши: сама ссылка в таблице сессий не лежит. Открытие чужой ссылки сюда не пишет."""

SESSION_KEY = "guest_orders"
MAX_LINKS = 20


def remember(request, token_hash: str) -> None:
    hashes = [h for h in request.session.get(SESSION_KEY, []) if h != token_hash]
    request.session[SESSION_KEY] = [*hashes, token_hash][-MAX_LINKS:]


def take(request) -> list[str]:
    return request.session.pop(SESSION_KEY, [])
