# Generated for the bookshop project (initial schema).
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
        ("customers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Sale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("receipt_no", models.CharField(max_length=30, unique=True)),
                ("sale_date", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("discount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("tax", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("payment_status", models.CharField(choices=[("paid", "Paid"), ("partial", "Partially paid"), ("credit", "Credit (unpaid)")], default="paid", max_length=10)),
                ("amount_paid", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("amount_due", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("customer", models.ForeignKey(blank=True, help_text="Null = walk-in customer.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales", to="customers.customer")),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sales", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-sale_date"],
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("method", models.CharField(choices=[("cash", "Cash"), ("card", "Card"), ("transfer", "Bank transfer"), ("credit", "On credit")], max_length=10)),
                ("payment_date", models.DateTimeField(auto_now_add=True)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sale_payments", to="customers.customer")),
                ("sale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="sales.sale")),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="SaleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=12)),
                ("discount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=12)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sale_items", to="catalog.product")),
                ("sale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="items", to="sales.sale")),
            ],
            options={
                "indexes": [models.Index(fields=["product", "sale"], name="sales_salei_product_3a7c1d_idx")],
            },
        ),
        migrations.CreateModel(
            name="Return",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("refund_method", models.CharField(choices=[("cash", "Cash refund"), ("credit", "Credit against balance")], default="credit", max_length=10)),
                ("return_date", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="returns", to="catalog.product")),
                ("sale", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="returns", to="sales.sale")),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
