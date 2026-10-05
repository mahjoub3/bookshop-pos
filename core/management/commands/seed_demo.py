"""Seed demo data: ~20 products, 3 customers, 1 supplier, 1 week of sales.

Usage: python manage.py seed_demo
Idempotent: skips if products already exist.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Category, Product, Supplier
from customers.models import Customer
from inventory.services import post_transaction
from sales import services as sale_services

BOOKS = [
    ("The Midnight Library", "Matt Haig", "9780525559474", "Fiction"),
    ("Atomic Habits", "James Clear", "9780735211292", "Self-help"),
    ("Mathematics Grade 8", "MoE Press", "9789990001008", "Textbook"),
    ("Mathematics Grade 9", "MoE Press", "9789990001107", "Textbook"),
    ("English Grammar Workbook", "Oxford", "9780190002005", "Textbook"),
    ("Science Explorer 7", "Pearson", "9780130003001", "Textbook"),
    ("A Brief History of Time", "Stephen Hawking", "9780553380163", "Science"),
    ("The Alchemist", "Paulo Coelho", "9780062315007", "Fiction"),
    ("Biology Grade 10", "MoE Press", "9789990004009", "Textbook"),
    ("World Atlas 2025", "National Geographic", "9781426220003", "Reference"),
]

STATIONERY = [
    ("A4 Exercise Book 96pg", "Oxford", "STA-EXB-A4-96", "Notebooks"),
    ("Ballpoint Pen Blue (pack 10)", "Bic", "STA-PEN-BLU-10", "Pens"),
    ("HB Pencil (pack 12)", "Faber-Castell", "STA-PNC-HB-12", "Pens"),
    ("Geometry Set", "Maped", "STA-GEO-SET", "Geometry"),
    ("Scientific Calculator FX-82", "Casio", "STA-CALC-FX82", "Electronics"),
    ("A4 Ruled Paper 500sh", "Double A", "STA-PAP-A4-500", "Paper"),
    ("Stapler Medium", "Kangaro", "STA-STP-MD", "Desk"),
    ("Whiteboard Marker (pack 4)", "Pilot", "STA-WBM-4", "Pens"),
    ("Glue Stick 21g", "UHU", "STA-GLU-21", "Adhesives"),
    ("Ruler 30cm", "Maped", "STA-RUL-30", "Geometry"),
]


class Command(BaseCommand):
    help = "Create demo data: products, customers, supplier, a week of sales."

    @transaction.atomic
    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("Products already exist — skipping seed.")
            return

        admin = User.objects.filter(is_superuser=True).first()
        if admin is None:
            admin = User.objects.create_superuser("admin", "admin@example.com", "admin")
            self.stdout.write("Created superuser admin/admin — change this password!")

        supplier = Supplier.objects.create(
            name="Central Book Distributors", phone="+1 555 0100",
            email="orders@cbd.example", address="12 Warehouse Rd",
        )

        products = []
        for (title, author, code, cat_name) in BOOKS:
            category, _ = Category.objects.get_or_create(name=cat_name)
            cost = Decimal(random.randint(300, 1500)) / 100
            p = Product.objects.create(
                type="book", title=title, author=author, isbn=code,
                sku=f"BK-{code[-6:]}", barcode=code, publisher=author and "Various",
                category=category, cost_price=cost,
                sell_price=(cost * Decimal("1.4")).quantize(Decimal("0.01")),
                reorder_level=3,
            )
            products.append(p)
        for (title, brand, sku, cat_name) in STATIONERY:
            category, _ = Category.objects.get_or_create(name=cat_name)
            cost = Decimal(random.randint(50, 800)) / 100
            p = Product.objects.create(
                type="stationery", title=title, author="", publisher=brand,
                sku=sku, barcode=f"6{random.randint(10**11, 10**12 - 1)}",
                category=category, cost_price=cost,
                sell_price=(cost * Decimal("1.5")).quantize(Decimal("0.01")),
                reorder_level=5,
            )
            products.append(p)

        # Opening stock via the ledger
        for p in products:
            post_transaction(
                product=p, txn_type="adjustment",
                quantity_delta=random.randint(10, 40), unit_cost=p.cost_price,
                reference_type="seed", note="Opening stock (demo)", user=admin,
            )

        customers = [
            Customer.objects.create(
                name="Riverside School", phone="+1 555 0111",
                credit_limit=Decimal("5000.00"), address="4 School Lane",
            ),
            Customer.objects.create(
                name="Amina Yusuf", phone="+1 555 0122",
                credit_limit=Decimal("300.00"),
            ),
            Customer.objects.create(
                name="Hope Academy", phone="+1 555 0133",
                credit_limit=Decimal("2500.00"), address="18 College Ave",
            ),
        ]

        # One week of sales
        for days_ago in range(7, 0, -1):
            for _ in range(random.randint(2, 6)):
                chosen = random.sample(products, k=random.randint(1, 4))
                cart = {"items": {}, "customer_id": None, "discount": "0.00"}
                for p in chosen:
                    cart["items"][str(p.pk)] = {
                        "qty": random.randint(1, 3),
                        "price": str(p.sell_price),
                        "discount": "0.00",
                    }
                on_credit = random.random() < 0.3
                customer = random.choice(customers) if on_credit else (
                    random.choice([None] + customers)
                )
                totals = sale_services.cart_totals(cart)
                payments = []
                if not on_credit:
                    payments = [{"method": random.choice(["cash", "card"]), "amount": totals["total"]}]

                sale = sale_services.create_sale(
                    user=admin, cart=cart, payments=payments, customer=customer,
                    allow_negative_stock=True, override_credit_limit=True,
                )
                # Backdate the sale + its ledger entries
                when = timezone.now() - timedelta(
                    days=days_ago, hours=random.randint(0, 8), minutes=random.randint(0, 59)
                )
                sale.sale_date = when
                sale.save(update_fields=["sale_date"])
                from inventory.models import InventoryTransaction
                from sales.models import Payment as PaymentModel

                InventoryTransaction.objects.filter(
                    reference_type="sale", reference_id=sale.pk
                ).update(created_at=when)
                PaymentModel.objects.filter(sale=sale).update(payment_date=when)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {len(products)} products, {len(customers)} customers, "
            f"1 supplier, ~1 week of sales."
        ))
