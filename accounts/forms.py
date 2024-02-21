# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User

class StandardUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

# from django.contrib.auth.forms import UserCreationForm
# from django import forms
#
# class CustomUserCreationForm(UserCreationForm):
#     full_name = forms.CharField(max_length=100, required=True)
#     address = forms.CharField(max_length=255, required=True)
#     phone_number = forms.CharField(max_length=20, required=True)
#
#     class Meta(UserCreationForm.Meta):
#         fields = UserCreationForm.Meta.fields + ('full_name', 'address', 'phone_number')

class ProfileUpdateForm(UserChangeForm):
    new_password = forms.CharField(label='new_password', widget=forms.PasswordInput(), required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            return new_password
        return None

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user