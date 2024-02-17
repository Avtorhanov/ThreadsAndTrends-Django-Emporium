# models.py
from django.contrib.auth.models import User
from django.db import models

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

    def __str__(self):
        return self.name

    # Допустимые варианты для статуса товара
    STATUS_CHOICES = [
        ('В наличии', 'В наличии'),
        ('Нет в наличии', 'Нет в наличии'),
        ('Снято с поставок', 'Снято с поставок'),
    ]
    # Поле выбора для статуса товара
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='В наличии')

class Cart(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=32, null=True, blank=True)  # Используется для неавторизованных пользователей
    products = models.ManyToManyField('Product', through='CartItem')

    def __str__(self):
        return f"Cart for {self.owner}"

    def calculate_total_price(self):
        total_price = sum(item.quantity * item.product.price for item in self.cartitem_set.all())
        return total_price

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"{self.quantity} of {self.product} in cart"

class Order(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    date_ordered = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_ordered = models.BooleanField(default=False)
    address = models.CharField(max_length=255, default='')
    phone_number = models.CharField(max_length=20, default='')
    full_name = models.CharField(max_length=100, default='')
    order_number = models.CharField(max_length=50, default='')  # Поле для уникального номера заказа
    user_order_number = models.IntegerField(default=0)  # Поле для уникального номера заказа пользователя

    STATUS_CHOICES = [
        ('В обработке', 'В обработке'),
        ('В пути', 'В пути'),
        ('Доставлено', 'Доставлено'),
        ('Отменен', 'Отменен'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Оформлен и находится в обработке')

    def __str__(self):
        return f"Order #{self.id} by {self.owner.username}"

    def total_quantity(self):
        return sum(item.quantity for item in self.orderitem_set.all())

    def generate_user_order_number(self):
        max_user_order_number = Order.objects.filter(owner=self.owner).aggregate(models.Max('user_order_number'))['user_order_number__max']
        new_user_order_number = max_user_order_number + 1 if max_user_order_number is not None else 1
        return new_user_order_number

    def save(self, *args, **kwargs):
        if not self.id:
            self.user_order_number = self.generate_user_order_number()
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} of {self.product} in order #{self.order.id}"
