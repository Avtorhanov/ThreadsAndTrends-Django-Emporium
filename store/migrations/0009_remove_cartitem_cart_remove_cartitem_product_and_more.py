# Generated by Django 5.0.1 on 2024-01-24 08:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_product_available_quantity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cartitem',
            name='cart',
        ),
        migrations.RemoveField(
            model_name='cartitem',
            name='product',
        ),
        migrations.RemoveField(
            model_name='product',
            name='available_quantity',
        ),
        migrations.DeleteModel(
            name='Cart',
        ),
        migrations.DeleteModel(
            name='CartItem',
        ),
    ]