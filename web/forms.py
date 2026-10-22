"""Формы витрины: только разбор и проверка ввода. Бизнес-правила — в сервисах
(accounts.services, store.services.cart, orders.services.checkout)."""

import re

from django import forms

from orders.models import DeliveryMethod, PaymentMethod
from store.services.storefront import Sort

MAX_RUBLES = 100_000_000  # как MAX_PRICE_KOPECKS каталога: защита от переполнения


def parse_rubles(value: str) -> int | None:
    """«1 990», «1990,5», «1990.50» → копейки (int) без float. Пусто или мусор → None."""
    raw = re.sub(r"[\s ]", "", value or "").replace(",", ".")
    match = re.fullmatch(r"(\d{1,9})(?:\.(\d{1,2}))?", raw)
    if not match:
        return None
    rubles = int(match.group(1))
    if rubles > MAX_RUBLES:
        return None
    kopecks = int((match.group(2) or "0").ljust(2, "0"))
    return rubles * 100 + kopecks


class CatalogFilterForm(forms.Form):
    """GET-параметры ленты: поиск, цена «от/до» в рублях, наличие, сортировка.
    Неверные значения не ошибка — параметр просто не применяется (ссылки из поисковиков)."""

    q = forms.CharField(required=False, max_length=100)
    price_min = forms.CharField(required=False, max_length=20)
    price_max = forms.CharField(required=False, max_length=20)
    in_stock = forms.BooleanField(required=False)
    sort = forms.ChoiceField(required=False, choices=[("", "")] + Sort.CHOICES)

    def values(self) -> dict:
        if not self.is_valid():
            data = {name: self.data.get(name, "") for name in self.fields}
            data["q"] = str(data["q"])[:100]
            data["sort"] = data["sort"] if data["sort"] in dict(Sort.CHOICES) else ""
            data["in_stock"] = data["in_stock"] in ("1", "on", "true")
        else:
            data = self.cleaned_data
        price_min = parse_rubles(data["price_min"])
        price_max = parse_rubles(data["price_max"])
        if price_min is not None and price_max is not None and price_min > price_max:
            price_min, price_max = price_max, price_min
        return {
            "q": " ".join(str(data["q"]).split()),
            "price_min": price_min,
            "price_max": price_max,
            "in_stock": bool(data["in_stock"]),
            "sort": data["sort"],
        }


class AddToCartForm(forms.Form):
    variant = forms.IntegerField(min_value=1, error_messages={"required": "Выберите размер."})
    quantity = forms.IntegerField(min_value=1, max_value=99, required=False)


class CartLineForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, max_value=99)


# --- Аккаунт ---

PASSWORD = {"autocomplete": "current-password"}
NEW_PASSWORD = {"autocomplete": "new-password"}


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email"})
    )
    password = forms.CharField(
        label="Пароль", max_length=128, strip=False, widget=forms.PasswordInput(attrs=PASSWORD)
    )


class RegisterForm(forms.Form):
    first_name = forms.CharField(
        label="Имя",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    email = forms.EmailField(
        label="Email", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email"})
    )
    password = forms.CharField(
        label="Пароль",
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs=NEW_PASSWORD),
        help_text="Не меньше 8 символов, не только цифры.",
    )
    # 152-ФЗ: согласие на обработку персональных данных — отдельной отметкой.
    consent = forms.BooleanField(
        label="Согласен на обработку персональных данных",
        error_messages={"required": "Без согласия на обработку данных зарегистрироваться нельзя."},
    )


class ResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email"})
    )


class ResetConfirmForm(forms.Form):
    email = forms.EmailField(
        label="Email", max_length=254, widget=forms.EmailInput(attrs={"autocomplete": "email"})
    )
    code = forms.RegexField(
        label="Код из письма",
        regex=r"^\d{6}$",
        error_messages={"invalid": "Код — 6 цифр из письма."},
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "maxlength": 6}
        ),
    )
    new_password = forms.CharField(
        label="Новый пароль",
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs=NEW_PASSWORD),
    )


class ProfileForm(forms.Form):
    first_name = forms.CharField(label="Имя", max_length=150, required=False)
    last_name = forms.CharField(label="Фамилия", max_length=150, required=False)


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label="Текущий пароль",
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs=PASSWORD),
    )
    new_password = forms.CharField(
        label="Новый пароль",
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs=NEW_PASSWORD),
    )


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Пароль", max_length=128, strip=False, widget=forms.PasswordInput(attrs=PASSWORD)
    )


# --- Оформление ---


class CheckoutForm(forms.Form):
    """Поля экрана оформления. Проверку имени, телефона и адреса делает сервис оформления
    (те же правила, что у приложения); форма — только формат."""

    delivery_method = forms.ChoiceField(choices=DeliveryMethod.choices, widget=forms.RadioSelect)
    payment_method = forms.ChoiceField(choices=PaymentMethod.choices, widget=forms.RadioSelect)
    recipient_name = forms.CharField(
        label="Имя и фамилия",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    recipient_phone = forms.CharField(
        label="Телефон",
        max_length=32,
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
    )
    delivery_address = forms.CharField(
        label="Адрес доставки",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "autocomplete": "street-address"}),
    )
    comment = forms.CharField(
        label="Комментарий к заказу",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    # Сумма и ключ попытки из отрисованной страницы: сервис сверит сумму, повтор сабмита
    # с тем же ключом вернёт уже созданный заказ.
    expected_total = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    idempotency_key = forms.RegexField(regex=r"^[A-Za-z0-9_-]{8,64}$", widget=forms.HiddenInput)

    def __init__(self, *args, delivery_methods=(), payment_methods=(), **kwargs):
        super().__init__(*args, **kwargs)
        # Только доступные сейчас способы (самовывоз — если задан адрес пункта, онлайн — если
        # включена оплата).
        self.fields["delivery_method"].choices = [
            (value, label) for value, label in DeliveryMethod.choices if value in delivery_methods
        ]
        self.fields["payment_method"].choices = [
            (value, label) for value, label in PaymentMethod.choices if value in payment_methods
        ]
