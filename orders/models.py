from django.contrib.auth.models import User
from django.db import models

from store.models import Product


# Create your models here.
class Order(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    date_ordered = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_ordered = models.BooleanField(default=False)
    address = models.CharField(max_length=255, default='')
    phone_number = models.CharField(max_length=20, default='')
    full_name = models.CharField(max_length=100, default='')

    # Допустимые варианты для статуса заказа
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    # Поле выбора для статуса заказа
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')

    def __str__(self):
        return f"Order #{self.id} by {self.owner.username}"

    def total_quantity(self):
        return sum(item.quantity for item in self.orderitem_set.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} of {self.product} in order #{self.order.id}"

    # Допустимые варианты для статуса товара
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('out_of_stock', 'Out of Stock'),
        ('discontinued', 'Discontinued'),
    ]
    # Поле выбора для статуса товара
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')