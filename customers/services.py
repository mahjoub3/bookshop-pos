"""Customer credit / receivables logic.

Balance formula (derived, never stored):
    balance = Σ sale.total
            − Σ POS payments (Payment) for this customer
            − Σ settlement payments (CustomerPayment)
            − Σ value of returns refunded as credit
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from sales.models import Payment, Return, Sale

from .models import Customer, CustomerPayment

ZERO = Decimal("0.00")


def _sum(qs, field):
    return qs.aggregate(s=Sum(field))["s"] or ZERO


def get_balance(customer):
    sales_total = _sum(Sale.objects.filter(customer=customer), "total")
    pos_paid = _sum(Payment.objects.filter(customer=customer), "amount")
    settled = _sum(CustomerPayment.objects.filter(customer=customer), "amount")
    # Return.value is unit_price * quantity — not directly aggregatable:
    credit_returns = sum(
        (r.value for r in Return.objects.filter(
            sale__customer=customer, refund_method=Return.RefundMethod.CREDIT
        )),
        ZERO,
    )
    return sales_total - pos_paid - settled - credit_returns


def credit_warnings(customer, extra_amount=ZERO):
    """Return warning string if extra_amount would exceed the credit limit."""
    projected = get_balance(customer) + Decimal(extra_amount)
    if projected > customer.credit_limit:
        return (
            f"Balance would be {projected} — over the credit limit "
            f"of {customer.credit_limit}."
        )
    return None


@transaction.atomic
def record_payment(*, customer, amount, method, user, sale=None, note=""):
    """Record a settlement payment. If `sale` is given, also sync its
    amount_paid / amount_due / payment_status."""
    amount = Decimal(amount)
    if amount <= ZERO:
        raise ValidationError("Payment amount must be greater than zero.")
    payment = CustomerPayment.objects.create(
        customer=customer, sale=sale, amount=amount,
        method=method, user=user, note=note,
    )
    if sale is not None:
        sale.amount_paid += amount
        sale.amount_due = max(sale.total - sale.amount_paid, ZERO)
        if sale.amount_due == ZERO:
            sale.payment_status = Sale.PaymentStatus.PAID
        elif sale.amount_paid > ZERO:
            sale.payment_status = Sale.PaymentStatus.PARTIAL
        sale.save(update_fields=["amount_paid", "amount_due", "payment_status"])
    return payment


def aging_report(customer=None):
    """Receivables aging via FIFO allocation of payments against sales.

    Returns list of dicts: customer, current, days30, days60, days90, total.
    Buckets: current ≤ 30 days, 31–60, 61–90, 90+.
    """
    today = timezone.localdate()
    customers = (
        [customer] if customer
        else Customer.objects.filter(is_active=True).order_by("name")
    )
    report = []
    for cust in customers:
        sales = list(
            Sale.objects.filter(customer=cust).order_by("sale_date")
        )
        if not sales:
            continue
        # Effective charge per sale = total − credit-refunded returns.
        charges = []
        for sale in sales:
            returned = sum(
                (r.value for r in sale.returns.all()
                 if r.refund_method == Return.RefundMethod.CREDIT),
                ZERO,
            )
            charges.append({"sale": sale, "effective": sale.total - returned})
        pool = (
            _sum(Payment.objects.filter(customer=cust), "amount")
            + _sum(CustomerPayment.objects.filter(customer=cust), "amount")
        )
        buckets = {"current": ZERO, "days30": ZERO, "days60": ZERO, "days90": ZERO}
        total_due = ZERO
        for charge in charges:
            due = charge["effective"]
            applied = min(pool, due)
            pool -= applied
            due -= applied
            if due <= ZERO:
                continue
            age = (today - timezone.localtime(charge["sale"].sale_date).date()).days
            if age <= 30:
                buckets["current"] += due
            elif age <= 60:
                buckets["days30"] += due
            elif age <= 90:
                buckets["days60"] += due
            else:
                buckets["days90"] += due
            total_due += due
        if total_due > ZERO:
            report.append({"customer": cust, **buckets, "total": total_due})
    return report


def statement_lines(customer, start=None, end=None):
    """Chronological statement lines with running balance."""
    events = []
    sales = Sale.objects.filter(customer=customer)
    if start:
        sales = sales.filter(sale_date__date__gte=start)
    if end:
        sales = sales.filter(sale_date__date__lte=end)
    for sale in sales:
        events.append({
            "date": sale.sale_date, "kind": "Sale", "ref": sale.receipt_no,
            "debit": sale.total, "credit": None,
        })
        for ret in sale.returns.filter(refund_method=Return.RefundMethod.CREDIT):
            events.append({
                "date": ret.return_date, "kind": "Return (credit)",
                "ref": f"{sale.receipt_no} / {ret.product}",
                "debit": None, "credit": ret.value,
            })
    pos_payments = Payment.objects.filter(customer=customer)
    settlements = CustomerPayment.objects.filter(customer=customer)
    if start:
        pos_payments = pos_payments.filter(payment_date__date__gte=start)
        settlements = settlements.filter(payment_date__date__gte=start)
    if end:
        pos_payments = pos_payments.filter(payment_date__date__lte=end)
        settlements = settlements.filter(payment_date__date__lte=end)
    for p in pos_payments:
        events.append({
            "date": p.payment_date, "kind": f"Payment ({p.get_method_display()})",
            "ref": p.sale.receipt_no, "debit": None, "credit": p.amount,
        })
    for p in settlements:
        events.append({
            "date": p.payment_date, "kind": f"Payment ({p.get_method_display()})",
            "ref": p.sale.receipt_no if p.sale else "—",
            "debit": None, "credit": p.amount,
        })
    events.sort(key=lambda e: e["date"])
    balance = ZERO
    for e in events:
        balance += (e["debit"] or ZERO) - (e["credit"] or ZERO)
        e["balance"] = balance
    return events


def overdue_customers():
    """Customers with anything in the 30+ buckets — dashboard KPI."""
    return [row for row in aging_report()
            if row["days30"] or row["days60"] or row["days90"]]
