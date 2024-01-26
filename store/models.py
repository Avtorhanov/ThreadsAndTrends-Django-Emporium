# models.py
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Product(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='product_images/')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, null=True, blank=True)
    users = models.ManyToManyField(User, related_name='user_products')

    def __str__(self):
        return self.name

class Cart(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=32, null=True, blank=True)  # Используется для неавторизованных пользователей
    products = models.ManyToManyField('Product', through='CartItem')

    def __str__(self):
        return f"Cart for {self.owner} ({self.session_key})"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"{self.quantity} of {self.product} in cart"



