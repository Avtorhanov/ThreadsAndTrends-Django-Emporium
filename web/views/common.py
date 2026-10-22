"""Общие помощники view витрины."""

from functools import wraps

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlencode


def is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def error_messages(exc: ValidationError) -> list[str]:
    """Тексты ошибки сервиса для покупателя (без названий полей)."""
    return list(exc.messages)


def flash_errors(request, exc: ValidationError) -> None:
    for text in error_messages(exc):
        messages.error(request, text)


def safe_next(request, default: str) -> str:
    """Адрес возврата из ?next= / поля формы — только на этот же сайт."""
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default


def customer_required(view):
    """Только вошедший покупатель. Гостя — на вход с возвратом на эту страницу."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("web:login")
            return redirect(f"{login_url}?{urlencode({'next': request.get_full_path()})}")
        return view(request, *args, **kwargs)

    return wrapper
