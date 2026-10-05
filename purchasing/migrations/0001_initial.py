# Generated for the bookshop project (initial schema).
import django.db.models.deletion
import django.utils.timezone
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
            name="PurchaseOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("ordered", "Ordered"), ("received", "Received"), ("cancelled", "Cancelled")], default="draft", max_length=10)),
                ("order_date", models.DateField(default=django.utils.timezone.localdate)),
                ("received_date", models.DateField(blank=True, null=True)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="purchase_orders", to="catalog.supplier")),
            ],
            options={
                "ordering": ["-order_date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="PurchaseOrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity_ordered", models.PositiveIntegerField()),
                ("quantity_received", models.PositiveIntegerField(default=0)),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=12)),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=12)),
                ("po", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="purchasing.purchaseorder")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="po_items", to="catalog.product")),
            ],
        ),
    ]
