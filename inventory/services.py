"""Stock business logic. The ledger is the source of truth."""
from django.db import transaction
from django.db.models import Sum

from catalog.models import Product

from .models import InventoryTransaction


def current_stock(product):
    """True stock from the ledger (bypasses the cache)."""
    total = InventoryTransaction.objects.filter(product=product).aggregate(
        s=Sum("quantity_delta")
    )["s"]
    return total or 0


def post_transaction(*, product, txn_type, quantity_delta, unit_cost=None,
                     reference_type="", reference_id=None, note="", user=None):
    """Append a row to the ledger. Caller wraps in transaction.atomic()."""
    if quantity_delta == 0:
        raise ValueError("quantity_delta must not be zero.")
    txn = InventoryTransaction.objects.create(
        product=product, txn_type=txn_type, quantity_delta=quantity_delta,
        unit_cost=unit_cost, reference_type=reference_type,
        reference_id=reference_id, note=note, user=user,
    )
    return txn


def adjust_stock(*, product, delta, reason, user, txn_type="adjustment"):
    """Manual adjustment / damage write-off."""
    if not reason.strip():
        raise ValueError("An adjustment reason is required.")
    with transaction.atomic():
        return post_transaction(
            product=product, txn_type=txn_type, quantity_delta=delta,
            unit_cost=product.cost_price, reference_type="manual",
            note=reason, user=user,
        )


def stocktake(*, counts, user, note="Stocktake"):
    """counts: {product_id: counted_qty}. Creates a correction per mismatch.

    Returns the list of created transactions.
    """
    created = []
    with transaction.atomic():
        products = Product.objects.filter(pk__in=counts.keys()).select_for_update()
        for product in products:
            counted = counts[product.pk]
            diff = counted - product.current_stock
            if diff:
                created.append(post_transaction(
                    product=product, txn_type="stocktake", quantity_delta=diff,
                    unit_cost=product.cost_price, reference_type="stocktake",
                    note=f"{note}: counted {counted}, system {product.current_stock}",
                    user=user,
                ))
    return created


def low_stock_products():
    """Active products at or below their (effective) reorder level."""
    return [p for p in Product.objects.filter(is_active=True).select_related("category")
            if p.is_low_stock]


def rebuild_stock_cache():
    """Recompute Product.current_stock for every product from the ledger."""
    sums = dict(
        InventoryTransaction.objects.values_list("product")
        .annotate(s=Sum("quantity_delta"))
        .values_list("product", "s")
    )
    updated = 0
    with transaction.atomic():
        for product in Product.objects.all():
            true_stock = sums.get(product.pk, 0) or 0
            if product.current_stock != true_stock:
                product.current_stock = true_stock
                product.save(update_fields=["current_stock"])
                updated += 1
    return updated
