from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """Ошибки сервисного слоя (django ValidationError) → 400 в формате DRF.

    PermissionDenied и Http404 из Django DRF обрабатывает сам.
    """
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "error_dict"):
            detail = {field: [str(m) for m in msgs] for field, msgs in exc.message_dict.items()}
        else:
            detail = {"non_field_errors": exc.messages}
        exc = exceptions.ValidationError(detail)
    return drf_exception_handler(exc, context)
