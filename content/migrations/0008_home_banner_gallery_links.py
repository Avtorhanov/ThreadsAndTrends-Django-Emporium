import django.db.models.deletion
from django.db import migrations, models


def images_to_list(apps, schema_editor):
    HomeBlock = apps.get_model("content", "HomeBlock")
    for block in HomeBlock.objects.exclude(image=None).only("id", "image_id"):
        HomeBlock.objects.filter(pk=block.pk).update(image_ids=[block.image_id])


def list_to_image(apps, schema_editor):
    HomeBlock = apps.get_model("content", "HomeBlock")
    for block in HomeBlock.objects.only("id", "image_ids"):
        if block.image_ids:
            HomeBlock.objects.filter(pk=block.pk).update(image_id=block.image_ids[0])


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0007_themesettings_default_text"),
        ("store", "0011_product_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="homeblock",
            name="image_ids",
            field=models.JSONField(blank=True, default=list, verbose_name="Картинки"),
        ),
        migrations.RunPython(images_to_list, list_to_image),
        migrations.RemoveField(model_name="homeblock", name="image"),
        migrations.AddField(
            model_name="homeblock",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="store.product",
                verbose_name="Товар",
            ),
        ),
        migrations.AddField(
            model_name="homeblock",
            name="links",
            field=models.JSONField(blank=True, default=list, verbose_name="Вкладки ленты"),
        ),
    ]
