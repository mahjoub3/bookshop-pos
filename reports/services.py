"""Report queries: sales, profit, best sellers, dead stock.

Profit rules (see README):
    line profit  = (unit_price - unit_cost) * quantity - line discount
    gross profit = Σ line profits over period  − return reversals
    net profit   = gross profit − expenses
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from inventory.models import InventoryTransaction
from sales.models import Return, Sale, SaleItem

from .models import Expense

ZERO = Decimal("0.00")


def _period_bounds(start, end):
    """Inclusive date range → aware datetime bounds."""
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start, time.min), tz)
    end_dt = timezone.make_aware(
        datetime.combine(end + timedelta(days=1), time.min), tz
    )
    return start_dt, end_dt


def daily_sales_summary(day):
    """Cash drawer report for one day."""
    start, end = _period_bounds(day, day)
    sales = Sale.objects.filter(sale_date__gte=start, sale_date__lt=end)
    payments = (
        sales.values_list("payments__method")
        .annotate(total=Sum("payments__amount"))
    )
    by_method = defaultdict(lambda: ZERO)
    for method, total in payments:
        if method:
            by_method[method] += total
    aggregates = sales.aggregate(
        count=Count("id"), total=Sum("total"),
        paid=Sum("amount_paid"), due=Sum("amount_due"),
        discount=Sum("discount"), tax=Sum("tax"),
    )
    profit = sum((s.profit for s in sales.prefetch_related("items")), ZERO)
    return {
        "day": day,
        "count": aggregates["count"] or 0,
        "total": aggregates["total"] or ZERO,
        "paid": aggregates["paid"] or ZERO,
        "due": aggregates["due"] or ZERO,
        "discount": aggregates["discount"] or ZERO,
        "tax": aggregates["tax"] or ZERO,
        "by_method": dict(by_method),
        "profit": profit,
    }


def profit_report(start, end, group_by="day"):
    """Gross/net profit grouped by day | product | category | supplier."""
    start_dt, end_dt = _period_bounds(start, end)
    items = (
        SaleItem.objects.filter(sale__sale_date__gte=start_dt, sale__sale_date__lt=end_dt)
        .select_related("sale", "product__category")
    )
    supplier_map = {}
    if group_by == "supplier":
        supplier_map = _supplier_names_for({i.product_id for i in items})
    rows = defaultdict(lambda: {"revenue": ZERO, "cost": ZERO, "discount": ZERO,
                                "profit": ZERO, "qty": 0})
    for item in items:
        if group_by == "day":
            key = timezone.localtime(item.sale.sale_date).date().isoformat()
        elif group_by == "product":
            key = item.product.title
        elif group_by == "category":
            key = item.product.category.name if item.product.category else "Uncategorized"
        elif group_by == "supplier":
            key = supplier_map.get(item.product_id) or "Unknown"
        else:
            key = str(item.sale_id)
        row = rows[key]
        row["revenue"] += item.unit_price * item.quantity
        row["cost"] += item.unit_cost * item.quantity
        row["discount"] += item.discount
        row["profit"] += item.line_profit
        row["qty"] += item.quantity

    # Subtract return reversals in the period
    returns = Return.objects.filter(
        return_date__gte=start_dt, return_date__lt=end_dt
    ).select_related("sale", "product")
    total_reversals = sum((r.profit_reversal for r in returns), ZERO)

    gross = sum((r["profit"] for r in rows.values()), ZERO) - total_reversals
    expenses = (
        Expense.objects.filter(expense_date__gte=start, expense_date__lte=end)
        .aggregate(s=Sum("amount"))["s"] or ZERO
    )
    table = [{"key": k, **v} for k, v in sorted(rows.items())]
    return {
        "rows": table,
        "gross_profit": gross,
        "return_reversals": total_reversals,
        "expenses": expenses,
        "net_profit": gross - expenses,
        "group_by": group_by,
        "start": start,
        "end": end,
    }


def _supplier_names_for(product_ids):
    """Map product_id -> supplier name via each product's most recent purchase
    (2 queries total, no N+1)."""
    from purchasing.models import PurchaseOrder

    txns = (
        InventoryTransaction.objects.filter(
            product_id__in=product_ids,
            txn_type=InventoryTransaction.TxnType.PURCHASE,
            reference_type="po",
        )
        .order_by("product_id", "-created_at")
        .values_list("product_id", "reference_id")
    )
    product_po = {}
    for product_id, po_id in txns:
        product_po.setdefault(product_id, po_id)  # first seen = most recent
    pos = PurchaseOrder.objects.filter(pk__in=set(product_po.values())) \
        .select_related("supplier")
    po_supplier = {po.pk: po.supplier.name for po in pos}
    return {pid: po_supplier.get(po_id) for pid, po_id in product_po.items()}


def best_sellers(start, end, limit=10):
    start_dt, end_dt = _period_bounds(start, end)
    return (
        SaleItem.objects.filter(sale__sale_date__gte=start_dt, sale__sale_date__lt=end_dt)
        .values("product__id", "product__title", "product__type")
        .annotate(qty=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-qty")[:limit]
    )


def dead_stock(days=90):
    """Active products with no sale in the last N days but stock on hand."""
    from catalog.models import Product

    since = timezone.now() - timedelta(days=days)
    recent_ids = (
        SaleItem.objects.filter(sale__sale_date__gte=since)
        .values_list("product_id", flat=True).distinct()
    )
    return [
        p for p in Product.objects.filter(is_active=True, current_stock__gt=0)
        .exclude(pk__in=recent_ids).select_related("category")
    ]


def sales_chart_data(days=30):
    """Daily revenue for the dashboard Chart.js line chart."""
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)
    start_dt, end_dt = _period_bounds(start, end)
    rows = (
        Sale.objects.filter(sale_date__gte=start_dt, sale_date__lt=end_dt)
        .annotate(day=TruncDate("sale_date"))
        .values("day").annotate(total=Sum("total"))
    )
    by_day = {r["day"]: r["total"] for r in rows}
    labels, data = [], []
    day = start
    while day <= end:
        labels.append(day.strftime("%d %b"))
        data.append(float(by_day.get(day, ZERO)))
        day += timedelta(days=1)
    return {"labels": labels, "data": data}


def expenses_in_period(start, end):
    return Expense.objects.filter(
        expense_date__gte=start, expense_date__lte=end
    ).select_related("user")
