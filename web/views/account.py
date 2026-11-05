"""Аккаунт покупателя на витрине: вход, регистрация, сброс пароля, профиль.

Вход — сессия Django (cookie httpOnly) + CSRF. Правила (валидаторы паролей, коды сброса,
мягкое удаление) — accounts.services; лимиты попыток общие с API приложения (web.ratelimit).
Администратор входит здесь же: после входа — сразу в панель /panel/ (тот же домен, та же
сессия Django, поэтому панель открывается без второго входа). Страницы покупателя ему не нужны.
"""

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from accounts import services as accounts
from orders.models import Order, OrderStatus
from store.services import history
from store.services.cart import MergeNoticeReason

from .. import cart as web_cart
from .. import ratelimit, theme
from ..forms import (
    AvatarForm,
    DeleteAccountForm,
    EmailChangeForm,
    EmailCodeForm,
    LoginForm,
    PasswordChangeForm,
    ProfileForm,
    RegisterForm,
    ResetConfirmForm,
    ResetRequestForm,
)
from .common import customer_required, safe_next

PANEL_URL = "/panel/"


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
        if request.user.is_staff:
            return redirect(PANEL_URL)
        return redirect(safe_next(request, reverse("web:profile")))
    form = LoginForm(request.POST or None)
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
                # Гостевая корзина администратору не переносится: он не покупатель.
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                return redirect(PANEL_URL)
            else:
                _login_with_cart(request, user)
                return redirect(safe_next(request, reverse("web:profile")))
    return render(
        request,
        "web/account/login.html",
        {
            "form": form,
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
                if user is not None and user.is_staff:
                    # Сотрудник по приглашению: пароль задан — дальше вход в панель.
                    messages.success(request, "Пароль задан. Войдите в панель магазина.")
                    return redirect(PANEL_URL)
                if user is not None:
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


PURCHASES_ON_PROFILE = 3
VIEWED_ON_PROFILE = 12


def profile(request):
    """Профиль: фото и имя, текущий заказ, полученные покупки, корзина, «Вы смотрели»."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(PANEL_URL)
    if not request.user.is_authenticated:
        # Профиль гостя — «Войти» и «Зарегистрироваться», как в приложении.
        return render(request, "web/account/guest.html", {"tab": "profile", "noindex": True})
    user = request.user
    orders = Order.objects.filter(owner=user)
    current = orders.unfinished().order_by("-created_at", "-id").first()
    delivered = orders.filter(status=OrderStatus.DELIVERED)
    purchases = list(
        delivered.order_by("-created_at", "-id").prefetch_related("items")[:PURCHASES_ON_PROFILE]
    )
    return render(
        request,
        "web/account/profile.html",
        {
            "current_order": current,
            "purchases": purchases,
            "purchases_count": delivered.count() if purchases else 0,
            "cart_summary": web_cart.summary(request),
            "viewed": history.recent_products(user, limit=VIEWED_ON_PROFILE),
            "tab": "profile",
            "noindex": True,
        },
    )


def _render_data(request, **forms):
    """Личные данные: фото, имя и фамилия, email (смена с кодом на новый адрес) и пароль.
    Форма с ошибками передаётся из своего обработчика, остальные — пустые."""
    user = request.user
    context = {
        "form": forms.get("form")
        or ProfileForm(initial={"first_name": user.first_name, "last_name": user.last_name}),
        "avatar_form": AvatarForm(),
        "email_form": forms.get("email_form") or EmailChangeForm(),
        "code_form": forms.get("code_form") or EmailCodeForm(),
        "password_form": forms.get("password_form") or PasswordChangeForm(),
        "pending_email": accounts.pending_email_change(user),
        "tab": "profile",
        "noindex": True,
    }
    return render(request, "web/account/data.html", context)


@customer_required
def profile_data(request):
    """Личные данные: фото профиля, имя и фамилия."""
    if request.method != "POST":
        return _render_data(request)
    form = ProfileForm(request.POST)
    if form.is_valid():
        accounts.update_profile(
            request.user,
            first_name=form.cleaned_data["first_name"].strip(),
            last_name=form.cleaned_data["last_name"].strip(),
        )
        messages.success(request, "Данные сохранены.")
        return redirect("web:profile_data")
    return _render_data(request, form=form)


@require_POST
@customer_required
def email_change(request):
    """Смена email, шаг 1: пароль + новый адрес → код на новый адрес."""
    if request.POST.get("cancel"):
        accounts.cancel_email_change(request.user)
        messages.success(request, "Смена email отменена.")
        return redirect(reverse("web:profile_data") + "#email")
    form = EmailChangeForm(request.POST)
    if form.is_valid():
        if not ratelimit.allow(request, "auth_sensitive"):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            try:
                record = accounts.request_email_change(
                    request.user,
                    new_email=form.cleaned_data["new_email"],
                    password=form.cleaned_data["password"],
                )
            except ValidationError as exc:
                _apply_errors(form, exc)
            else:
                messages.success(request, f"Код отправлен на {record.new_email}.")
                return redirect(reverse("web:profile_data") + "#email")
    return _render_data(request, email_form=form)


@require_POST
@customer_required
def email_change_confirm(request):
    """Смена email, шаг 2: код с нового адреса."""
    form = EmailCodeForm(request.POST)
    if form.is_valid():
        if not ratelimit.allow(request, "auth_sensitive"):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            try:
                user = accounts.confirm_email_change(request.user, code=form.cleaned_data["code"])
            except ValidationError as exc:
                _apply_errors(form, exc)
            else:
                messages.success(request, f"Email изменён: теперь входите с {user.email}.")
                return redirect(reverse("web:profile_data") + "#email")
    return _render_data(request, code_form=form)


@require_POST
@customer_required
def avatar(request):
    """Загрузить (поле avatar) или удалить (remove=1) фото профиля."""
    if not ratelimit.allow(request, "avatar_upload", user=request.user):
        messages.error(request, ratelimit.TOO_MANY)
    elif request.POST.get("remove"):
        accounts.remove_avatar(request.user)
        messages.success(request, "Фото удалено.")
    else:
        form = AvatarForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, "Выберите файл с фото.")
        else:
            try:
                accounts.set_avatar(request.user, form.cleaned_data["avatar"])
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            else:
                messages.success(request, "Фото обновлено.")
    return redirect("web:profile_data")


def profile_look(request):
    """Оформление витрины: тема, палитра, углы, размер текста (и гостю — выбор в cookie)."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(PANEL_URL)
    return render(
        request,
        "web/account/look.html",
        {**theme.options(request), "tab": "profile", "noindex": True},
    )


@require_POST
@customer_required
def viewed_clear(request):
    history.clear(request.user)
    messages.success(request, "История просмотров очищена.")
    return redirect("web:profile")


@customer_required
def password_change(request):
    """Смена пароля — блок на странице «Личные данные» (отдельной страницы больше нет)."""
    if request.method != "POST":
        return redirect(reverse("web:profile_data") + "#password")
    form = PasswordChangeForm(request.POST)
    if form.is_valid():
        if not ratelimit.allow(request, "auth_sensitive"):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            try:
                accounts.update_password(
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
                return redirect(reverse("web:profile_data") + "#password")
    return _render_data(request, password_form=form)


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
