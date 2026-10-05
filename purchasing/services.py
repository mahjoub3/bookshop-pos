"""Purchasing business logic: receiving POs and supplier returns."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory.services import post_transaction

from .models import PurchaseOrder


def receive_po(*, po, receipts, user):
    """Record received quantities: {item_id: qty_now_received}.

    Partial receiving allowed. Creates ledger entries and updates
    Product.cost_price using LAST COST. Supplier balance increases by
    the value received.
    """
    if po.status in (PurchaseOrder.Status.CANCELLED,):
        raise ValidationError("Cannot receive against a cancelled PO.")
    received_value = Decimal("0.00")
    with transaction.atomic():
        items = po.items.select_for_update().select_related("product").in_bulk()
        for item_id, qty in receipts.items():
            if qty <= 0:
                continue
            item = items.get(int(item_id))
            if item is None or item.po_id != po.pk:
                raise ValidationError("Invalid PO line.")
            if item.quantity_received + qty > item.quantity_ordered:
                raise ValidationError(
                    f"Receiving more than ordered for '{item.product.title}'."
                )
            item.quantity_received += qty
            item.save(update_fields=["quantity_received"])
            post_transaction(
                product=item.product, txn_type="purchase", quantity_delta=qty,
                unit_cost=item.unit_cost, reference_type="po",
                reference_id=po.pk, note=f"Received on PO-{po.pk}", user=user,
            )
            # LAST COST update
            product = item.product
            product.cost_price = item.unit_cost
            product.save(update_fields=["cost_price"])
            received_value += item.unit_cost * qty

        po.refresh_from_db()
        if po.fully_received:
            po.status = PurchaseOrder.Status.RECEIVED
            po.received_date = timezone.localdate()
        elif po.status == PurchaseOrder.Status.DRAFT:
            po.status = PurchaseOrder.Status.ORDERED
        po.save()

        supplier = po.supplier
        supplier.balance += received_value
        supplier.save(update_fields=["balance"])
    return po


def return_to_supplier(*, supplier, product, quantity, unit_cost, reason, user):
    """Send stock back to a supplier: stock out + supplier balance down."""
    if quantity <= 0:
        raise ValidationError("Quantity must be positive.")
    with transaction.atomic():
        if product.current_stock < quantity:
            raise ValidationError(
                f"Not enough stock to return: have {product.current_stock}."
            )
        post_transaction(
            product=product, txn_type="return_out", quantity_delta=-quantity,
            unit_cost=unit_cost, reference_type="supplier_return",
            note=reason, user=user,
        )
        supplier.balance -= unit_cost * quantity
        supplier.save(update_fields=["balance"])
