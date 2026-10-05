# Generated for the bookshop project (initial schema).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Setting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("shop_name", models.CharField(default="My Book & Stationery Shop", max_length=120)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("tax_rate", models.DecimalField(decimal_places=2, default=0, help_text="Sales tax percentage applied at POS, e.g. 7.50 for 7.5%.", max_digits=5)),
                ("receipt_header", models.CharField(blank=True, max_length=255)),
                ("receipt_footer", models.CharField(blank=True, default="Thank you for shopping with us!", max_length=255)),
                ("currency", models.CharField(default="$", max_length=8)),
                ("low_stock_threshold", models.PositiveIntegerField(default=5, help_text="Fallback reorder level when a product has none set.")),
                ("logo", models.ImageField(blank=True, null=True, upload_to="branding/")),
            ],
            options={
                "verbose_name": "Shop setting",
                "verbose_name_plural": "Shop settings",
            },
        ),
    ]
