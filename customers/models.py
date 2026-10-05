from decimal import Decimal

from django.conf import settings
from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CustomerPayment(models.Model):
    """A payment settling credit, made after the sale (vs. Payment at POS)."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        TRANSFER = "transfer", "Bank transfer"

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="payments"
    )
    sale = models.ForeignKey(
        "sales.Sale", null=True, blank=True,
        on_delete=models.PROTECT, related_name="settlement_payments",
        help_text="Optional: allocate directly to one sale.",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=Method.choices)
    payment_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.customer} — {self.amount}"
