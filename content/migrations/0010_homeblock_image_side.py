from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0009_theme_scale_wordmark"),
    ]

    operations = [
        migrations.AddField(
            model_name="homeblock",
            name="image_side",
            field=models.CharField(
                choices=[("top", "Сверху"), ("left", "Слева"), ("right", "Справа")],
                default="top",
                max_length=5,
                verbose_name="Картинка текста",
            ),
        ),
    ]
