
from django.contrib.auth.models import User
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Категория")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категорию"
        verbose_name_plural = "Категории"

class SubCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Подкатегория")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Категории")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Подкатегория"
        verbose_name_plural = "Подкатегории"

class Product(models.Model):
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    name = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    image = models.ImageField(upload_to='product_images/', verbose_name="Изображение")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Категория")
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Подкатегория")

    def __str__(self):
        return self.name

    # Допустимые варианты для статуса товара
    STATUS_CHOICES = [
        ('В наличии', 'В наличии'),
        ('Нет в наличии', 'Нет в наличии'),
        ('Снято с поставок', 'Снято с поставок'),
    ]
    # Поле выбора для статуса товара
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='В наличии', verbose_name="На складе")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

class Cart(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Покупатель")
    session_key = models.CharField(max_length=32, null=True, blank=True, verbose_name="Гость")
    products = models.ManyToManyField('Product', through='CartItem')

    def __str__(self):
        return f"Козина - {self.owner}"

    def calculate_total_price(self):
        total_price = sum(item.quantity * item.product.price for item in self.cartitem_set.all())
        return total_price

    class Meta:
        verbose_name = "Корзину"
        verbose_name_plural = "Корзины"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, verbose_name="Элемент из корзины")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="Цена")

    def __str__(self):
        return f"{self.quantity} из {self.product} в корзине"

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Элементы корзины"

