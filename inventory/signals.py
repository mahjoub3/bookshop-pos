from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import InventoryTransaction


@receiver(post_save, sender=InventoryTransaction)
def update_stock_cache(sender, instance, created, **kwargs):
    """Keep Product.current_stock in sync with the ledger (cache only)."""
    if created:
        product = instance.product
        type(product).objects.filter(pk=product.pk).update(
            current_stock=product.current_stock + instance.quantity_delta
        )
