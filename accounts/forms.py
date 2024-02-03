# accounts/forms.py
from django.contrib.auth.forms import UserCreationForm
from django import forms

class CustomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(max_length=100, required=True)
    address = forms.CharField(max_length=255, required=True)
    phone_number = forms.CharField(max_length=20, required=True)

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('full_name', 'address', 'phone_number')
