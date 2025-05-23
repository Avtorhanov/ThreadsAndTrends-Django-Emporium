# Generated by Django 5.0.2 on 2025-04-27 16:46

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('store', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_ordered', models.DateTimeField(auto_now_add=True, verbose_name='Дата оформления')),
                ('total_price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Общая стоимость')),
                ('is_ordered', models.BooleanField(default=False, verbose_name='Заказано')),
                ('address', models.CharField(default='', max_length=255, verbose_name='Адрес доставки')),
                ('phone_number', models.CharField(default='', max_length=20, verbose_name='Номер телефона')),
                ('full_name', models.CharField(default='', max_length=100, verbose_name='Полное Имя')),
                ('order_number', models.CharField(default='', max_length=50, verbose_name='Номер заказа')),
                ('user_order_number', models.IntegerField(default=0, verbose_name='Номер заказа клиента')),
                ('size', models.CharField(blank=True, default=' ', max_length=50, null=True, verbose_name='размер')),
                ('status', models.CharField(choices=[('В обработке', 'В обработке'), ('В пути', 'В пути'), ('Доставлен', 'Доставлен'), ('Отменен', 'Отменен')], default='В обработке', max_length=50, verbose_name='Статус')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Покупатель')),
            ],
            options={
                'verbose_name': 'Заказ',
                'verbose_name_plural': 'Оформленные заказы',
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Количество')),
                ('price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Цена')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Описание')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orders.order', verbose_name='Заказ')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.product', verbose_name='Товар')),
            ],
            options={
                'verbose_name': 'Элементы заказа',
            },
        ),
    ]
