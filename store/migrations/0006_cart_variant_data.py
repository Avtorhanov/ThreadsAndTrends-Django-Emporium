# Сессия 4, шаг 2 из 3: перенос позиций корзины на варианты.
#  - гостевые корзины (owner = NULL) удаляются: гостевая корзина теперь живёт на устройстве;
#  - у пользователя остаётся одна корзина (самая ранняя), лишние удаляются;
#  - позиция переходит на единственный неудалённый вариант товара; если вариантов
#    несколько (размер неизвестен) или нет ни одного — позиция удаляется;
#  - seen_price_kopecks = текущая цена товара (предупреждения после миграции не будет).
# Корзина — не история заказов, поэтому неоднозначные позиции не сохраняются.

from django.db import migrations


def forwards(apps, schema_editor):
    Cart = apps.get_model("store", "Cart")
    CartItem = apps.get_model("store", "CartItem")
    ProductVariant = apps.get_model("store", "ProductVariant")

    Cart.objects.filter(owner__isnull=True).delete()

    seen_owners = set()
    for cart in Cart.objects.order_by("pk").only("pk", "owner"):
        if cart.owner_id in seen_owners:
            cart.delete()
        else:
            seen_owners.add(cart.owner_id)

    for item in CartItem.objects.select_related("product"):
        variants = list(
            ProductVariant.objects.filter(
                product_id=item.product_id, deleted_at__isnull=True
            ).values_list("pk", flat=True)[:2]
        )
        if len(variants) != 1 or item.product.deleted_at is not None:
            item.delete()
            continue
        item.variant_id = variants[0]
        item.seen_price_kopecks = item.product.price_kopecks
        item.quantity = max(item.quantity, 1)
        item.save(update_fields=["variant", "seen_price_kopecks", "quantity"])


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0005_cart_variant_schema"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
