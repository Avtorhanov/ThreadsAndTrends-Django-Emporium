from django.db import migrations, models

import accounts.models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_staff_access"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar",
            field=models.ImageField(
                blank=True, upload_to=accounts.models.avatar_path, verbose_name="Фото профиля"
            ),
        ),
    ]
