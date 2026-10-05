# Generated for the bookshop project (initial schema).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="catalog.category")),
            ],
            options={
                "verbose_name_plural": "Categories",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Supplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("notes", models.TextField(blank=True)),
                ("balance", models.DecimalField(decimal_places=2, default=0, help_text="What we owe this supplier (positive) or credit with them (negative).", max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(choices=[("book", "Book"), ("stationery", "Stationery")], default="book", max_length=20)),
                ("isbn", models.CharField(blank=True, db_index=True, max_length=20, verbose_name="ISBN")),
                ("sku", models.CharField(blank=True, db_index=True, max_length=40, verbose_name="SKU")),
                ("barcode", models.CharField(blank=True, db_index=True, max_length=64)),
                ("title", models.CharField(db_index=True, max_length=255)),
                ("author", models.CharField(blank=True, max_length=160)),
                ("publisher", models.CharField(blank=True, max_length=160)),
                ("subject", models.CharField(blank=True, max_length=120)),
                ("grade_level", models.CharField(blank=True, max_length=60)),
                ("language", models.CharField(blank=True, max_length=60)),
                ("unit", models.CharField(choices=[("piece", "Piece"), ("pack", "Pack"), ("box", "Box")], default="piece", max_length=10)),
                ("pack_size", models.PositiveIntegerField(default=1)),
                ("cost_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("sell_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("reorder_level", models.PositiveIntegerField(default=0, help_text="0 = use the shop-wide low-stock threshold.")),
                ("is_active", models.BooleanField(default=True)),
                ("current_stock", models.IntegerField(default=0, editable=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to="catalog.category")),
            ],
            options={
                "ordering": ["title"],
                "indexes": [models.Index(fields=["type", "is_active"], name="catalog_pro_type_9b3f2f_idx")],
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("barcode", ""), _negated=True), fields=("barcode",), name="uniq_product_barcode"),
                    models.UniqueConstraint(condition=models.Q(("isbn", ""), _negated=True), fields=("isbn",), name="uniq_product_isbn"),
                    models.UniqueConstraint(condition=models.Q(("sku", ""), _negated=True), fields=("sku",), name="uniq_product_sku"),
                ],
            },
        ),
    ]
