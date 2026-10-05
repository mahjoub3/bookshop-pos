"""Sales business logic: session cart, checkout, returns.

Views stay thin — everything money-changing goes through here,
inside transaction.atomic().
"""
from decimal import Decimal

from django.conf import settings as dj_settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from catalog.models import Product
from core.models import Setting
from core.utils import next_receipt_no
from inventory.services import post_transaction

from .models import Payment, Return, Sale, SaleItem

ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# Session cart
# ---------------------------------------------------------------------------

def get_cart(request):
    cart = request.session.setdefault(dj_settings.CART_SESSION_KEY, {})
    cart.setdefault("items", {})
    cart.setdefault("customer_id", None)
    cart.setdefault("discount", "0.00")
    return cart


def save_cart(request, cart):
    request.session[dj_settings.CART_SESSION_KEY] = cart
    request.session.modified = True


def cart_add(request, product, qty=1, price=None):
    cart = get_cart(request)
    key = str(product.pk)
    item = cart["items"].setdefault(key, {"qty": 0, "price": str(product.sell_price), "discount": "0.00"})
    item["qty"] += qty
    if price is not None:
        item["price"] = str(price)
    save_cart(request, cart)
    return cart


def cart_update(request, product_id, qty=None, price=None, discount=None):
    cart = get_cart(request)
    key = str(product_id)
    item = cart["items"].get(key)
    if not item:
        return cart
    if qty is not None:
        if qty <= 0:
            cart["items"].pop(key, None)
        else:
            item["qty"] = qty
    if price is not None:
        item["price"] = str(price)
    if discount is not None:
        item["discount"] = str(discount)
    save_cart(request, cart)
    return cart


def cart_remove(request, product_id):
    cart = get_cart(request)
    cart["items"].pop(str(product_id), None)
    save_cart(request, cart)
    return cart


def cart_clear(request):
    request.session[dj_settings.CART_SESSION_KEY] = {"items": {}, "customer_id": None, "discount": "0.00"}
    request.session.modified = True


def cart_lines(cart):
    """Enriched cart lines: [{product, qty, price, discount, line_total}]."""
    ids = [int(pk) for pk in cart["items"].keys()]
    products = Product.objects.filter(pk__in=ids).in_bulk()
    lines = []
    for key, item in cart["items"].items():
        product = products.get(int(key))
        if not product:
            continue
        price = Decimal(item["price"])
        discount = Decimal(item.get("discount", "0.00"))
        lines.append({
            "product": product, "qty": item["qty"], "price": price,
            "discount": discount, "line_total": price * item["qty"] - discount,
        })
    return lines


def cart_totals(cart):
    """Return dict(subtotal, discount, tax, total) as Decimals."""
    lines = cart_lines(cart)
    subtotal = sum((l["price"] * l["qty"] for l in lines), ZERO)
    line_discounts = sum((l["discount"] for l in lines), ZERO)
    cart_discount = Decimal(cart.get("discount") or "0.00")
    taxable = subtotal - line_discounts - cart_discount
    if taxable < ZERO:
        taxable = ZERO
    tax_rate = Setting.load().tax_rate
    tax = (taxable * tax_rate / 100).quantize(ZERO)
    return {
        "subtotal": subtotal,
        "discount": line_discounts + cart_discount,
        "tax": tax,
        "total": taxable + tax,
    }


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

def create_sale(*, user, cart, payments, customer=None, notes="",
                allow_negative_stock=False, override_credit_limit=False):
    """Create a Sale from the session cart.

    payments: list of {"method": "cash|card|transfer", "amount": Decimal}.
    Any unpaid remainder becomes credit (requires a customer).
    Raises ValidationError on any business-rule violation.
    """
    lines = cart_lines(cart)
    if not lines:
        raise ValidationError("Cannot save a sale with zero items.")

    totals = cart_totals(cart)
    total = totals["total"]

    paid = ZERO
    for p in payments:
        amount = Decimal(str(p["amount"]))
        if amount <= ZERO:
            raise ValidationError("Payment amounts must be greater than zero.")
        if p["method"] not in (Payment.Method.CASH, Payment.Method.CARD, Payment.Method.TRANSFER):
            raise ValidationError(f"Invalid payment method '{p['method']}'.")
        paid += amount
    if paid > total:
        raise ValidationError("Payments exceed the sale total.")
    amount_due = total - paid

    if amount_due > ZERO and customer is None:
        raise ValidationError("A credit (unpaid) sale requires a customer.")

    if customer is not None and amount_due > ZERO:
        from customers.services import get_balance

        new_balance = get_balance(customer) + amount_due
        if new_balance > customer.credit_limit and not override_credit_limit:
            raise ValidationError(
                f"Credit limit exceeded: balance would be {new_balance} "
                f"(limit {customer.credit_limit}). Manager/admin override required."
            )

    with transaction.atomic():
        # Lock products and validate stock
        products = {
            p.pk: p
            for p in Product.objects.select_for_update()
            .filter(pk__in=[l["product"].pk for l in lines])
        }
        for line in lines:
            product = products[line["product"].pk]
            if not allow_negative_stock and product.current_stock < line["qty"]:
                raise ValidationError(
                    f"Not enough stock for '{product.title}': "
                    f"have {product.current_stock}, need {line['qty']}."
                )

        sale = Sale.objects.create(
            receipt_no=next_receipt_no(),
            customer=customer,
            subtotal=totals["subtotal"],
            discount=totals["discount"],
            tax=totals["tax"],
            total=total,
            amount_paid=paid,
            amount_due=amount_due,
            payment_status=(
                Sale.PaymentStatus.PAID if amount_due == ZERO
                else Sale.PaymentStatus.CREDIT if paid == ZERO
                else Sale.PaymentStatus.PARTIAL
            ),
            user=user,
            notes=notes,
        )

        for line in lines:
            product = products[line["product"].pk]
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=line["qty"],
                unit_price=line["price"],
                unit_cost=product.cost_price,  # COST SNAPSHOT
                discount=line["discount"],
                line_total=line["line_total"],
            )
            post_transaction(
                product=product, txn_type="sale", quantity_delta=-line["qty"],
                unit_cost=product.cost_price, reference_type="sale",
                reference_id=sale.pk, note=f"Sale {sale.receipt_no}", user=user,
            )

        for p in payments:
            Payment.objects.create(
                sale=sale, customer=customer,
                amount=Decimal(str(p["amount"])), method=p["method"], user=user,
            )

    return sale


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

def quantity_returned(sale, product):
    return Return.objects.filter(sale=sale, product=product).aggregate(
        s=Sum("quantity")
    )["s"] or 0


def process_return(*, sale, product, quantity, refund_method, reason, user):
    """Customer return: restock + refund cash or credit against balance."""
    if quantity <= 0:
        raise ValidationError("Return quantity must be greater than zero.")
    try:
        item = SaleItem.objects.get(sale=sale, product=product)
    except SaleItem.DoesNotExist:
        raise ValidationError("That product is not on this sale.")
    already = quantity_returned(sale, product)
    if already + quantity > item.quantity:
        raise ValidationError(
            f"Cannot return {quantity}: only {item.quantity - already} left to return."
        )

    with transaction.atomic():
        ret = Return.objects.create(
            sale=sale, product=product, quantity=quantity,
            unit_price=item.unit_price, reason=reason,
            refund_method=refund_method, user=user,
        )
        post_transaction(
            product=product, txn_type="return_in", quantity_delta=quantity,
            unit_cost=item.unit_cost, reference_type="return",
            reference_id=ret.pk, note=f"Return for {sale.receipt_no}: {reason}",
            user=user,
        )
        # Keep the sale's due amount in sync for credit sales.
        if refund_method == Return.RefundMethod.CREDIT and sale.amount_due > ZERO:
            reduction = min(ret.value, sale.amount_due)
            sale.amount_due -= reduction
            sale.amount_paid = sale.total - sale.amount_due
            if sale.amount_due == ZERO:
                sale.payment_status = Sale.PaymentStatus.PAID
            sale.save(update_fields=["amount_due", "amount_paid", "payment_status"])
    return ret
