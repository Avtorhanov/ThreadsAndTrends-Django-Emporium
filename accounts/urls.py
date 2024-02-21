# accounts/urls.py
from django.urls import path
from .views import signup, log_in_view, log_out_view, profile

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', log_in_view, name='login'),
    path('logout/', log_out_view, name='logout'),
    path('profile/', profile, name='profile'),
]
