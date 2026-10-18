from django import forms


class ProductSearchForm(forms.Form):
    query = forms.CharField(max_length=100, label="Search")


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Your Name")
    email = forms.EmailField(label="Your Email")
    message = forms.CharField(widget=forms.Textarea, label="Your Message")
