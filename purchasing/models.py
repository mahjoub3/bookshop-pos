from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ORDERED = "ordered", "Ordered"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    supplier = models.ForeignKey(
        "catalog.Supplier", on_delete=models.PROTECT, related_name="purchase_orders"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    order_date = models.DateField(default=timezone.localdate)
    received_date = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-order_date", "-id"]

    def __str__(self):
        return f"PO-{self.pk} ({self.supplier})"

    def recompute_total(self):
        total = sum(
            (i.line_total for i in self.items.all()), Decimal("0.00")
        )
        self.total = total
        self.save(update_fields=["total"])

    @property
    def fully_received(self):
        return all(i.quantity_received >= i.quantity_ordered for i in self.items.all())


class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="po_items"
    )
    quantity_ordered = models.PositiveIntegerField()
    quantity_received = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.line_total = self.unit_cost * self.quantity_ordered
        super().save(*args, **kwargs)

    @property
    def outstanding(self):
        return self.quantity_ordered - self.quantity_received
