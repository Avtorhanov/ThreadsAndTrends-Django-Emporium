from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import StandardUserCreationForm, ProfileUpdateForm


def signup(request):
    if request.method == 'POST':
        form = StandardUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f'Приветствуем вас, {user.username}! Вы успешно зарегистрированы.')
            return redirect('home')
    else:
        form = StandardUserCreationForm()

    return render(request, 'accounts/signup.html', {'form': form})


def log_in_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'С приехалом, {user.username}!')
            return redirect('home')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})

@login_required
def log_out_view(request):
    auth_logout(request)
    messages.success(request, 'Вы вышли из магазина.')
    return redirect('home')


@login_required
def profile(request):
    user = request.user

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            new_password = form.cleaned_data.get('new_password')
            if new_password:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'пароль обновлен.')
            else:
                messages.success(request, 'Данные обновлены.')
            return redirect('profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле '{form.fields[field].label}': {error}")
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, 'accounts/profile.html', {'form': form})






