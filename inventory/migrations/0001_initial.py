# Generated for the bookshop project (initial schema).
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("txn_type", models.CharField(choices=[("purchase", "Purchase (received)"), ("sale", "Sale"), ("return_in", "Customer return (restock)"), ("return_out", "Return to supplier"), ("adjustment", "Manual adjustment"), ("damage", "Damage / write-off"), ("stocktake", "Stocktake correction")], max_length=20)),
                ("quantity_delta", models.IntegerField(help_text="Positive = stock in, negative = stock out.")),
                ("unit_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("reference_type", models.CharField(blank=True, max_length=40)),
                ("reference_id", models.PositiveIntegerField(blank=True, null=True)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_transactions", to="catalog.product")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="inventory_transactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["product", "created_at"], name="inventory_t_product_6f8c1a_idx"),
                    models.Index(fields=["txn_type", "created_at"], name="inventory_t_txn_typ_2d4e6b_idx"),
                ],
            },
        ),
    ]
