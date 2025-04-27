# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.db import models
from store.models import Product


class Order(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Покупатель")
    date_ordered = models.DateTimeField(auto_now_add=True, verbose_name="Дата оформления")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="Общая стоимость")
    is_ordered = models.BooleanField(default=False, verbose_name="Заказано")
    address = models.CharField(max_length=255, default='', verbose_name="Адрес доставки")
    phone_number = models.CharField(max_length=20, default='', verbose_name="Номер телефона")
    full_name = models.CharField(max_length=100, default='', verbose_name="Полное Имя")
    order_number = models.CharField(max_length=50, default='', verbose_name="Номер заказа")
    user_order_number = models.IntegerField(default=0,  verbose_name="Номер заказа клиента")
    size = models.CharField(max_length=50, default=' ',null=True, blank=True, verbose_name="размер")

    # payment_choices = [(' ', ' '), ('оплата при получении', 'оплата при получении'), ('оплата картой', 'оплата картой')]
    # payment_method = models.CharField(max_length=20, choices=payment_choices, default=' ', verbose_name="способ оплаты")

    STATUS_CHOICES = [
        ('В обработке', 'В обработке'),
        ('В пути', 'В пути'),
        ('Доставлен', 'Доставлен'),
        ('Отменен', 'Отменен'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='В обработке', verbose_name="Статус")

    def __str__(self):
        return f"Номер заказа #{self.id} пользователя {self.owner.username}"

    def total_quantity(self):
        return f'{sum(item.quantity for item in self.orderitem_set.all())}'

    def generate_user_order_number(self):
        max_user_order_number = Order.objects.filter(owner=self.owner).aggregate(models.Max('user_order_number'))['user_order_number__max']
        new_user_order_number = max_user_order_number + 1 if max_user_order_number is not None else 1
        return new_user_order_number

    def save(self, *args, **kwargs):
        if not self.id:
            self.user_order_number = self.generate_user_order_number()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Оформленные заказы"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="Цена")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    def __str__(self):
        return f"{self.quantity} {self.product} в заказе #{self.order.id}"

    class Meta:
        verbose_name = 'Элементы заказа'