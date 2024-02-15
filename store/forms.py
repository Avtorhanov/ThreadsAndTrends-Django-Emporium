from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'subcategory', 'image']

class ProductSearchForm(forms.Form):
    query = forms.CharField(max_length=100, label='Search')

class OrderForm(forms.Form):
    full_name = forms.CharField(max_length=100, label='Full Name')
    address = forms.CharField(max_length=255, label='Address')
    phone_number = forms.CharField(max_length=20, label='Phone Number')


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label='Your Name')
    email = forms.EmailField(label='Your Email')
    message = forms.CharField(widget=forms.Textarea, label='Your Message')
