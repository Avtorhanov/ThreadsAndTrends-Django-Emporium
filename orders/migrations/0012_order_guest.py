import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Оформление без аккаунта: заказ без владельца с доступом по секретной ссылке."""

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("orders", "0011_orderitem_color_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="orders",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Покупатель",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="guest_token_hash",
            field=models.CharField(
                blank=True,
                db_default="",
                default="",
                max_length=64,
                verbose_name="Хеш гостевой ссылки",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="guest_link_expires_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Гостевая ссылка действует до"
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="guest_consent_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Согласие на обработку ПДн (гость)"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                condition=models.Q(("status", "awaiting_agreement")),
                fields=["recipient_phone"],
                name="order_phone_awaiting_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                condition=models.Q(("owner__isnull", True)),
                fields=["guest_link_expires_at"],
                name="order_guest_expiry_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.UniqueConstraint(
                condition=models.Q(("owner__isnull", True)),
                fields=("idempotency_key",),
                name="order_guest_unique_idempotency_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.UniqueConstraint(
                condition=models.Q(("owner__isnull", True)),
                fields=("guest_token_hash",),
                name="order_guest_unique_token",
            ),
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("guest_link_expires_at__isnull", True),
                        ("guest_token_hash", ""),
                        ("owner__isnull", False),
                    ),
                    models.Q(
                        ("guest_consent_at__isnull", False),
                        ("owner__isnull", True),
                        models.Q(("guest_token_hash", ""), negated=True),
                    ),
                    _connector="OR",
                ),
                name="order_guest_fields_consistent",
            ),
        ),
    ]
