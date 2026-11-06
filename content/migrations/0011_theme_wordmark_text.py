from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0010_homeblock_image_side"),
    ]

    operations = [
        migrations.AddField(
            model_name="themesettings",
            name="wordmark",
            field=models.CharField(
                db_default="shop", default="shop", max_length=6, verbose_name="Слово рядом с «DiDi»"
            ),
        ),
    ]
