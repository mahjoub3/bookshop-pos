from django.conf import settings
from django.db import models


class InventoryTransaction(models.Model):
    """APPEND-ONLY stock ledger. Never update or delete rows.

    Current stock for a product = SUM(quantity_delta) over its rows.
    Product.current_stock is only a cache of that sum (updated by signal;
    rebuild with `python manage.py rebuild_stock_cache`).
    """

    class TxnType(models.TextChoices):
        PURCHASE = "purchase", "Purchase (received)"
        SALE = "sale", "Sale"
        RETURN_IN = "return_in", "Customer return (restock)"
        RETURN_OUT = "return_out", "Return to supplier"
        ADJUSTMENT = "adjustment", "Manual adjustment"
        DAMAGE = "damage", "Damage / write-off"
        STOCKTAKE = "stocktake", "Stocktake correction"

    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="stock_transactions"
    )
    txn_type = models.CharField(max_length=20, choices=TxnType.choices)
    quantity_delta = models.IntegerField(help_text="Positive = stock in, negative = stock out.")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reference_type = models.CharField(max_length=40, blank=True)  # e.g. "sale", "po"
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="inventory_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "created_at"]),
            models.Index(fields=["txn_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_txn_type_display()} {self.quantity_delta:+d} — {self.product}"
