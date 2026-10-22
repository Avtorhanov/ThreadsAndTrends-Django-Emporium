"""Страницы ошибок в стиле витрины. 500 — без контекстных процессоров и запросов к БД:
при сбое базы страница всё равно отрисуется."""

from django.http import HttpResponseServerError
from django.shortcuts import render
from django.template.loader import get_template


def not_found(request, exception=None):
    return render(request, "web/errors/404.html", {"noindex": True}, status=404)


def server_error(request):
    return HttpResponseServerError(get_template("web/errors/500.html").render())
