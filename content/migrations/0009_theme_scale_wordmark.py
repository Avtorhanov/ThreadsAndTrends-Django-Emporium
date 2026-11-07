from django.db import migrations, models

# «Размер текста» s/m/l → масштаб в процентах; палитра «Солнце» убрана из tokens.json.
LEGACY_TEXT = {"s": "100", "m": "115", "l": "130"}
REMOVED_PALETTE = "sun"


def forwards(apps, schema_editor):
    ThemeSettings = apps.get_model("content", "ThemeSettings")
    for row in ThemeSettings.objects.all():
        row.default_text = LEGACY_TEXT.get(row.default_text, row.default_text)
        row.palettes = [key for key in row.palettes if key != REMOVED_PALETTE] or ["lime"]
        if row.default_palette not in row.palettes:
            row.default_palette = row.palettes[0]
        row.save(update_fields=["default_text", "palettes", "default_palette"])


def backwards(apps, schema_editor):
    ThemeSettings = apps.get_model("content", "ThemeSettings")
    reverse = {value: key for key, value in LEGACY_TEXT.items()}
    for row in ThemeSettings.objects.all():
        row.default_text = reverse.get(row.default_text, "s")
        row.save(update_fields=["default_text"])


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0008_home_banner_gallery_links"),
    ]

    operations = [
        migrations.AlterField(
            model_name="themesettings",
            name="default_text",
            field=models.CharField(default="100", max_length=3, verbose_name="Масштаб по умолчанию"),
        ),
        migrations.AddField(
            model_name="themesettings",
            name="show_wordmark",
            field=models.BooleanField(default=True, verbose_name="Слово «shop» в логотипе"),
        ),
        migrations.RunPython(forwards, backwards),
    ]
