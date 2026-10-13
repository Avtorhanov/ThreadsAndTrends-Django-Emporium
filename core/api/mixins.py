from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny

from core.api.permissions import IsAdmin


class AdminAPIMixin:
    """API панели администратора: только сессия Django (+ CSRF) и роль администратора.
    JWT мобильного клиента не принимается."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdmin]

    def get_authenticate_header(self, request):
        # 401 (а не 403) для неаутентифицированных: панель отличает «нужен вход» от «нет прав».
        return "Session"


class PublicAPIMixin:
    """Публичное чтение (каталог): без аутентификации, чтобы просроченный JWT
    в заголовке не превращал открытый запрос в 401."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
