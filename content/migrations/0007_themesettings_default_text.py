from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0006_themesettings_nav_style"),
    ]

    operations = [
        migrations.AddField(
            model_name="themesettings",
            name="default_text",
            field=models.CharField(
                default="s", max_length=2, verbose_name="Размер текста по умолчанию"
            ),
        ),
    ]
