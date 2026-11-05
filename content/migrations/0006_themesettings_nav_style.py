from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0005_theme_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="themesettings",
            name="nav_style",
            field=models.CharField(default="solid", max_length=10, verbose_name="Нижнее меню"),
        ),
    ]
