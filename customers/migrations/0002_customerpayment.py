# Generated for the bookshop project (customer payments settle credit sales).
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0001_initial"),
        ("sales", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("method", models.CharField(choices=[("cash", "Cash"), ("card", "Card"), ("transfer", "Bank transfer")], max_length=10)),
                ("payment_date", models.DateTimeField(auto_now_add=True)),
                ("note", models.CharField(blank=True, max_length=255)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="customers.customer")),
                ("sale", models.ForeignKey(blank=True, help_text="Optional: allocate directly to one sale.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="settlement_payments", to="sales.sale")),
                ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-payment_date"],
            },
        ),
    ]
