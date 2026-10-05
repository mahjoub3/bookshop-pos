from decimal import Decimal

from django.db import models
from django.db.models import Q


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.parent.name} › {self.name}" if self.parent else self.name


class Supplier(models.Model):
    name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="What we owe this supplier (positive) or credit with them (negative).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    class ProductType(models.TextChoices):
        BOOK = "book", "Book"
        STATIONERY = "stationery", "Stationery"

    class Unit(models.TextChoices):
        PIECE = "piece", "Piece"
        PACK = "pack", "Pack"
        BOX = "box", "Box"

    type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.BOOK)
    isbn = models.CharField("ISBN", max_length=20, blank=True, db_index=True)
    sku = models.CharField("SKU", max_length=40, blank=True, db_index=True)
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    title = models.CharField(max_length=255, db_index=True)
    author = models.CharField(max_length=160, blank=True)
    publisher = models.CharField(max_length=160, blank=True)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    subject = models.CharField(max_length=120, blank=True)
    grade_level = models.CharField(max_length=60, blank=True)
    language = models.CharField(max_length=60, blank=True)
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.PIECE)
    pack_size = models.PositiveIntegerField(default=1)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sell_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    reorder_level = models.PositiveIntegerField(
        default=0, help_text="0 = use the shop-wide low-stock threshold."
    )
    is_active = models.BooleanField(default=True)
    # Cached from the append-only inventory ledger. NEVER edit directly —
    # the ledger is the source of truth; run `rebuild_stock_cache` to fix.
    current_stock = models.IntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["barcode"], condition=~Q(barcode=""), name="uniq_product_barcode"
            ),
            models.UniqueConstraint(
                fields=["isbn"], condition=~Q(isbn=""), name="uniq_product_isbn"
            ),
            models.UniqueConstraint(
                fields=["sku"], condition=~Q(sku=""), name="uniq_product_sku"
            ),
        ]
        indexes = [models.Index(fields=["type", "is_active"])]

    def __str__(self):
        return self.title

    @property
    def effective_reorder_level(self):
        if self.reorder_level:
            return self.reorder_level
        from core.models import Setting

        return Setting.load().low_stock_threshold

    @property
    def is_low_stock(self):
        return self.current_stock <= self.effective_reorder_level

    @property
    def margin(self):
        if not self.sell_price:
            return Decimal("0")
        return (self.sell_price - self.cost_price) / self.sell_price * 100
