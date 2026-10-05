from decimal import Decimal

from django.db import models


class Setting(models.Model):
    """Singleton row (pk=1) holding shop-wide configuration."""

    shop_name = models.CharField(max_length=120, default="My Book & Stationery Shop")
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        help_text="Sales tax percentage applied at POS, e.g. 7.50 for 7.5%.",
    )
    receipt_header = models.CharField(max_length=255, blank=True)
    receipt_footer = models.CharField(max_length=255, blank=True, default="Thank you for shopping with us!")
    currency = models.CharField(max_length=8, default="$")
    low_stock_threshold = models.PositiveIntegerField(
        default=5, help_text="Fallback reorder level when a product has none set."
    )
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)

    class Meta:
        verbose_name = "Shop setting"
        verbose_name_plural = "Shop settings"

    def __str__(self):
        return self.shop_name

    @classmethod
    def load(cls):
        # Cheap process-level cache; invalidated on save. Settings change rarely.
        cached = getattr(cls, "_cached", None)
        if cached is not None:
            return cached
        obj, _ = cls.objects.get_or_create(pk=1)
        cls._cached = obj
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        type(self)._cached = self
