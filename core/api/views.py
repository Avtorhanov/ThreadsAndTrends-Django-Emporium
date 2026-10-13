import logging

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _check_database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        logger.exception("Healthcheck: база данных недоступна")
        return False


def _check_cache() -> bool:
    try:
        cache.set("healthcheck", "ok", timeout=10)
        return cache.get("healthcheck") == "ok"
    except Exception:
        logger.exception("Healthcheck: кэш недоступен")
        return False


class HealthView(APIView):
    """Liveness/readiness для Docker, балансировщика и мониторинга."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="Health",
                fields={
                    "status": serializers.ChoiceField(choices=["ok", "error"]),
                    "checks": serializers.DictField(child=serializers.BooleanField()),
                },
            ),
        },
        description="503 и status=error, если какая-либо проверка не прошла.",
    )
    def get(self, request, *args, **kwargs):
        checks = {"database": _check_database(), "cache": _check_cache()}
        healthy = all(checks.values())
        return Response(
            {"status": "ok" if healthy else "error", "checks": checks},
            status=200 if healthy else 503,
        )
