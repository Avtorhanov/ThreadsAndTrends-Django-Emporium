from django import forms


class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        max_length=100,
        required=True,
    )

    address = forms.CharField(
        max_length=255,
        required=True,
    )

    phone_number = forms.CharField(
        max_length=20,
        required=True,
    )

    size = forms.CharField(
        max_length=50,
        required=False,
    )