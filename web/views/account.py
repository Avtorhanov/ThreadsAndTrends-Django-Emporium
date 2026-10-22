"""Аккаунт покупателя на витрине: вход, регистрация, сброс пароля, профиль.

Вход — сессия Django (cookie httpOnly) + CSRF. Правила (валидаторы паролей, коды сброса,
мягкое удаление) — accounts.services; лимиты попыток общие с API приложения (web.ratelimit).
Администратор на витрине не входит: у него панель /panel/.
"""

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from accounts import services as accounts
from store.services.cart import MergeNoticeReason

from .. import cart as web_cart
from .. import ratelimit, theme
from ..forms import (
    DeleteAccountForm,
    LoginForm,
    PasswordChangeForm,
    ProfileForm,
    RegisterForm,
    ResetConfirmForm,
    ResetRequestForm,
)
from .common import customer_required, safe_next

STAFF_LOGIN = "Это учётная запись администратора — войдите в панель управления."


def _apply_errors(form, exc: ValidationError) -> None:
    """Ошибки сервиса → ошибки полей формы (поле, которого нет в форме, — общая ошибка)."""
    if hasattr(exc, "error_dict"):
        for field, errors in exc.error_dict.items():
            target = field if field in form.fields else None
            for error in errors:
                form.add_error(target, error.messages)
    else:
        form.add_error(None, exc.messages)


def _login_with_cart(request, user) -> None:
    """Вход + перенос гостевой корзины в корзину аккаунта, с объяснением пропущенного."""
    lines = web_cart.take_guest_lines(request)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    notices = web_cart.merge_into_account(request, lines)
    reasons = {notice.reason for notice in notices}
    if MergeNoticeReason.QUANTITY_LIMITED in reasons:
        messages.warning(request, "Количество некоторых товаров уменьшено до доступного.")
    if reasons & {MergeNoticeReason.UNAVAILABLE, MergeNoticeReason.OUT_OF_STOCK}:
        messages.warning(request, "Часть товаров из корзины закончилась и не перенесена.")
    if MergeNoticeReason.CART_FULL in reasons:
        messages.warning(request, "Корзина заполнена — не все товары перенесены.")


def login_view(request):
    if request.user.is_authenticated:
        return redirect(safe_next(request, reverse("web:profile")))
    form = LoginForm(request.POST or None)
    staff = False
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        if not (
            ratelimit.allow(request, "auth_login")
            and ratelimit.allow(request, "auth_login_email", email=email)
        ):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            user = accounts.authenticate_user(email=email, password=form.cleaned_data["password"])
            if user is None:
                form.add_error(None, "Неверный email или пароль.")
            elif user.is_staff:
                form.add_error(None, STAFF_LOGIN)
                staff = True
            else:
                _login_with_cart(request, user)
                return redirect(safe_next(request, reverse("web:profile")))
    return render(
        request,
        "web/account/login.html",
        {
            "form": form,
            "staff": staff,
            "next": safe_next(request, ""),
            "tab": "profile",
            "noindex": True,
        },
    )


@require_POST
def logout_view(request):
    logout(request)
    return redirect("web:home")


def register(request):
    if request.user.is_authenticated:
        return redirect("web:profile")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not ratelimit.allow(request, "auth_register"):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            try:
                user = accounts.register_customer(
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password"],
                    first_name=form.cleaned_data["first_name"].strip(),
                )
            except ValidationError as exc:
                _apply_errors(form, exc)
            else:
                _login_with_cart(request, user)
                messages.success(request, "Добро пожаловать в DiDi-shop!")
                return redirect(safe_next(request, reverse("web:profile")))
    return render(
        request,
        "web/account/register.html",
        {"form": form, "next": safe_next(request, ""), "tab": "profile", "noindex": True},
    )


def password_reset(request):
    form = ResetRequestForm(request.POST or None, initial={"email": request.GET.get("email", "")})
    if request.method == "POST" and form.is_valid():
        if not ratelimit.allow(request, "password_reset"):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            email = form.cleaned_data["email"]
            # Ответ одинаковый для любого email: наличие аккаунта не раскрывается.
            accounts.request_password_reset(email)
            confirm = reverse("web:password_reset_confirm")
            return redirect(f"{confirm}?{urlencode({'email': email})}")
    return render(
        request,
        "web/account/password_reset.html",
        {"form": form, "tab": "profile", "noindex": True},
    )


def password_reset_confirm(request):
    form = ResetConfirmForm(request.POST or None, initial={"email": request.GET.get("email", "")})
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        if not (
            ratelimit.allow(request, "password_reset_confirm")
            and ratelimit.allow(request, "password_reset_confirm_email", email=email)
        ):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            try:
                accounts.confirm_password_reset(
                    email=email,
                    code=form.cleaned_data["code"],
                    new_password=form.cleaned_data["new_password"],
                )
            except ValidationError as exc:
                _apply_errors(form, exc)
            else:
                user = accounts.authenticate_user(
                    email=email, password=form.cleaned_data["new_password"]
                )
                if user is not None and not user.is_staff:
                    _login_with_cart(request, user)
                    messages.success(request, "Пароль изменён, вы вошли в аккаунт.")
                    return redirect("web:profile")
                messages.success(request, "Пароль изменён. Войдите с новым паролем.")
                return redirect("web:login")
    return render(
        request,
        "web/account/password_reset_confirm.html",
        {"form": form, "tab": "profile", "noindex": True},
    )


def profile(request):
    if not request.user.is_authenticated:
        # Профиль гостя — «Войти» и «Зарегистрироваться», как в приложении.
        return render(
            request,
            "web/account/guest.html",
            {
                "theme_choices": theme.CHOICES,
                "theme_value": theme.get_theme(request) or theme.SYSTEM,
                "tab": "profile",
                "noindex": True,
            },
        )
    user = request.user
    form = ProfileForm(
        request.POST or None,
        initial={"first_name": user.first_name, "last_name": user.last_name},
    )
    if request.method == "POST" and form.is_valid():
        accounts.update_profile(
            user,
            first_name=form.cleaned_data["first_name"].strip(),
            last_name=form.cleaned_data["last_name"].strip(),
        )
        messages.success(request, "Профиль сохранён.")
        return redirect("web:profile")
    return render(
        request,
        "web/account/profile.html",
        {
            "form": form,
            "theme_choices": theme.CHOICES,
            "theme_value": theme.get_theme(request) or theme.SYSTEM,
            "tab": "profile",
            "noindex": True,
        },
    )


@customer_required
def password_change(request):
    form = PasswordChangeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not ratelimit.allow(request, "auth_sensitive"):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            try:
                accounts.change_password(
                    request.user,
                    old_password=form.cleaned_data["old_password"],
                    new_password=form.cleaned_data["new_password"],
                )
            except ValidationError as exc:
                _apply_errors(form, exc)
            else:
                # Эта сессия остаётся, остальные (другие браузеры) — выходят.
                update_session_auth_hash(request, request.user)
                messages.success(request, "Пароль изменён.")
                return redirect("web:profile")
    return render(
        request,
        "web/account/password_change.html",
        {"form": form, "tab": "profile", "noindex": True},
    )


@customer_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not ratelimit.allow(request, "auth_sensitive"):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            try:
                accounts.delete_own_account(request.user, password=form.cleaned_data["password"])
            except ValidationError as exc:
                _apply_errors(form, exc)
            except PermissionDenied as exc:
                form.add_error(None, str(exc))
            else:
                logout(request)
                messages.success(request, "Аккаунт удалён.")
                return redirect("web:home")
    return render(
        request,
        "web/account/delete.html",
        {"form": form, "tab": "profile", "noindex": True},
    )
