"""Catalog business logic: CSV import/export. Keep views thin."""
import csv
import io
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction

from .models import Category, Product


def parse_product_csv(uploaded_file):
    """Return (rows, errors). Each row is a dict of cleaned strings + _line."""
    try:
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["File must be UTF-8 encoded CSV."]
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "title" not in [f.strip().lower() for f in reader.fieldnames]:
        return [], ["CSV must contain at least a 'title' header column."]
    rows, errors = [], []
    for i, raw in enumerate(reader, start=2):
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        if not row.get("title"):
            errors.append(f"Line {i}: missing title — skipped.")
            continue
        bad = False
        for money in ("cost_price", "sell_price"):
            if row.get(money):
                try:
                    Decimal(row[money])
                except InvalidOperation:
                    errors.append(f"Line {i}: invalid {money} '{row[money]}' — skipped.")
                    bad = True
        if not bad:
            row["_line"] = i
            rows.append(row)
    return rows, errors


def import_products(rows, user=None):
    """Create/update products from parsed rows. Returns (created, updated, errors)."""
    created = updated = 0
    errors = []
    for row in rows:
        try:
            with transaction.atomic():
                category = None
                if row.get("category"):
                    category, _ = Category.objects.get_or_create(name=row["category"])
                defaults = {
                    "title": row["title"],
                    "type": row.get("type") if row.get("type") in ("book", "stationery") else "book",
                    "isbn": row.get("isbn", "")[:20],
                    "barcode": row.get("barcode", "")[:64],
                    "author": row.get("author", ""),
                    "publisher": row.get("publisher", ""),
                    "category": category,
                    "subject": row.get("subject", ""),
                    "grade_level": row.get("grade_level", ""),
                    "language": row.get("language", ""),
                    "unit": row.get("unit") if row.get("unit") in ("piece", "pack", "box") else "piece",
                    "pack_size": int(row.get("pack_size") or 1),
                    "cost_price": Decimal(row.get("cost_price") or "0"),
                    "sell_price": Decimal(row.get("sell_price") or "0"),
                    "reorder_level": int(row.get("reorder_level") or 0),
                }
                if row.get("sku"):
                    lookup = {"sku": row["sku"][:40]}
                elif row.get("barcode"):
                    lookup = {"barcode": row["barcode"][:64]}
                elif row.get("isbn"):
                    lookup = {"isbn": row["isbn"][:20]}
                else:
                    lookup = {"title": row["title"]}
                product, was_created = Product.objects.update_or_create(defaults=defaults, **lookup)
                created += int(was_created)
                updated += int(not was_created)
                opening = int(row.get("opening_stock") or 0)
                if was_created and opening:
                    from inventory.services import post_transaction

                    post_transaction(
                        product=product, txn_type="adjustment", quantity_delta=opening,
                        unit_cost=product.cost_price, reference_type="csv_import",
                        reference_id=None, note="Opening stock (CSV import)", user=user,
                    )
        except (IntegrityError, ValueError, InvalidOperation) as exc:
            errors.append(f"Line {row.get('_line', '?')}: {exc}")
    return created, updated, errors


def products_to_csv(queryset):
    """Export products to CSV text."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "title", "type", "isbn", "sku", "barcode", "author", "publisher",
        "category", "cost_price", "sell_price", "reorder_level", "current_stock",
    ])
    for p in queryset:
        writer.writerow([
            p.title, p.type, p.isbn, p.sku, p.barcode, p.author, p.publisher,
            p.category.name if p.category else "", p.cost_price, p.sell_price,
            p.reorder_level, p.current_stock,
        ])
    return buf.getvalue()
