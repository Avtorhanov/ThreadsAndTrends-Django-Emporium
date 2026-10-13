from django.conf import settings
from django.core.checks import Error, register

# Коды ЮKassa: https://yookassa.ru/developers/payment-acceptance/receipts/54fz/parameters-values
TAX_SYSTEM_CODES = range(1, 7)
PAYMENT_MODES = {"full_prepayment", "full_payment"}


@register()
def check_payment_settings(app_configs, **kwargs):
    errors = []
    if settings.ORDERS_ONLINE_PAYMENT_ENABLED and not (
        settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY
    ):
        errors.append(
            Error(
                "Онлайн-оплата включена, но ЮKassa не настроена.",
                hint="Задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY "
                "или выключите ORDERS_ONLINE_PAYMENT_ENABLED.",
                id="payments.E001",
            )
        )
    if settings.PAYMENTS_TAX_SYSTEM_CODE not in TAX_SYSTEM_CODES:
        errors.append(Error("PAYMENTS_TAX_SYSTEM_CODE должен быть от 1 до 6.", id="payments.E002"))
    if settings.PAYMENTS_VAT_CODE < 1:
        errors.append(
            Error("PAYMENTS_VAT_CODE — код ставки НДС ЮKassa (1 — без НДС).", id="payments.E003")
        )
    if settings.PAYMENTS_RECEIPT_PAYMENT_MODE not in PAYMENT_MODES:
        errors.append(
            Error(
                "PAYMENTS_RECEIPT_PAYMENT_MODE: full_payment или full_prepayment.",
                id="payments.E004",
            )
        )
    if not settings.PAYMENTS_RETURN_URL_PREFIXES:
        errors.append(
            Error(
                "PAYMENTS_RETURN_URL_PREFIXES пуст: приложение не сможет вернуться с оплаты.",
                id="payments.E005",
            )
        )
    return errors
