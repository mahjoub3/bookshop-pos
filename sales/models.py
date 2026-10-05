from decimal import Decimal

from django.conf import settings
from django.db import models


class Sale(models.Model):
    class PaymentStatus(models.TextChoices):
        PAID = "paid", "Paid"
        PARTIAL = "partial", "Partially paid"
        CREDIT = "credit", "Credit (unpaid)"

    receipt_no = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(
        "customers.Customer", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sales",
        help_text="Null = walk-in customer.",
    )
    sale_date = models.DateTimeField(auto_now_add=True, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PAID
    )
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="sales"
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-sale_date"]

    def __str__(self):
        return self.receipt_no

    @property
    def profit(self):
        return sum((item.line_profit for item in self.items.all()), Decimal("0.00"))


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="items")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="sale_items"
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    # SNAPSHOT of Product.cost_price at sale time — never changes afterwards,
    # so historical profit survives later cost updates.
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        indexes = [models.Index(fields=["product", "sale"])]

    def __str__(self):
        return f"{self.product} x{self.quantity}"

    @property
    def line_profit(self):
        return (self.unit_price - self.unit_cost) * self.quantity - self.discount


class Payment(models.Model):
    """Payment taken at the POS for a specific sale."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        TRANSFER = "transfer", "Bank transfer"
        CREDIT = "credit", "On credit"

    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="payments")
    customer = models.ForeignKey(
        "customers.Customer", null=True, blank=True,
        on_delete=models.PROTECT, related_name="sale_payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=Method.choices)
    payment_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.get_method_display()} {self.amount} — {self.sale.receipt_no}"


class Return(models.Model):
    """Customer return: restocks inventory and reverses profit."""

    class RefundMethod(models.TextChoices):
        CASH = "cash", "Cash refund"
        CREDIT = "credit", "Credit against balance"

    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="returns")
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="returns"
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    refund_method = models.CharField(
        max_length=10, choices=RefundMethod.choices, default=RefundMethod.CREDIT
    )
    return_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )

    @property
    def value(self):
        return self.unit_price * self.quantity

    @property
    def profit_reversal(self):
        item = SaleItem.objects.filter(sale=self.sale, product=self.product).first()
        cost = item.unit_cost if item else Decimal("0.00")
        return (self.unit_price - cost) * self.quantity
