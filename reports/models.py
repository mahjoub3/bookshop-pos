from decimal import Decimal

from django.conf import settings
from django.db import models


class Expense(models.Model):
    class Category(models.TextChoices):
        RENT = "rent", "Rent"
        UTILITIES = "utilities", "Utilities"
        SALARIES = "salaries", "Salaries"
        SUPPLIES = "supplies", "Supplies"
        TRANSPORT = "transport", "Transport"
        OTHER = "other", "Other"

    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date"]

    def __str__(self):
        return f"{self.get_category_display()}: {self.amount} ({self.expense_date})"
