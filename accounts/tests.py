from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from store.models import Cart, CartItem
from accounts.forms import StandardUserCreationForm, ProfileUpdateForm

class AccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')

    def test_signup_view(self):
        response = self.client.post(reverse('signup'), {'username': 'newuser', 'email': 'newuser@example.com', 'password1': 'newpassword', 'password2': 'newpassword'})
        self.assertEqual(response.status_code, 302)  

    def test_login_view(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'password'})
        self.assertEqual(response.status_code, 302)  

    def test_logout_view(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)  

    def test_profile_view(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)  

  
    def test_standard_user_creation_form(self):
        form_data = {'username': 'newuser', 'first_name': 'New', 'last_name': 'User', 'email': 'newuser@example.com', 'password1': 'password', 'password2': 'password'}
        form = StandardUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())  

    def test_profile_update_form(self):
        username = 'testuser1'  
        password = 'password123'
        user = User.objects.create_user(username=username, password=password)
        data = {
            'username': username,
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'new_password': 'newpassword123'
        }

        form = ProfileUpdateForm(data, instance=user)
        self.assertTrue(form.is_valid())
