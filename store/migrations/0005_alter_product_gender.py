# Generated by Django 5.0.1 on 2024-01-21 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_product_gender'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='gender',
            field=models.CharField(blank=True, choices=[('M', 'Man'), ('W', 'Women')], max_length=1, null=True),
        ),
    ]