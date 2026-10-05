from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from decimal import Decimal

from accounts.mixins import ManagerUpMixin
from core.models import Setting
from core.utils import date_range_from_request, parse_date
from customers.services import aging_report

from . import excel, pdf, services
from .models import Expense


def _export_or_render(request, *, context, template, title, headers, rows,
                      totals_row=None, filename="report"):
    """?format=xlsx|pdf exports; otherwise renders the HTML page."""
    fmt = request.GET.get("format")
    settings_obj = Setting.load()
    if fmt == "xlsx":
        data = excel.table_to_xlsx(sheet_title=title, headers=headers, rows=rows)
        response = HttpResponse(
            data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        return response
    if fmt == "pdf":
        data = pdf.generic_report_pdf(
            settings_obj=settings_obj, title=title,
            headers=headers, rows=rows, totals_row=totals_row,
        )
        response = HttpResponse(data, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}.pdf"'
        return response
    return render(request, template, context)


class DailySalesView(ManagerUpMixin, View):
    def get(self, request):
        day = parse_date(request.GET.get("day"), timezone.localdate())
        summary = services.daily_sales_summary(day)
        headers = ["Metric", "Value"]
        rows = [
            ["Date", str(summary["day"])],
            ["Transactions", summary["count"]],
            ["Total sales", f'{summary["total"]:.2f}'],
            ["Collected", f'{summary["paid"]:.2f}'],
            ["On credit", f'{summary["due"]:.2f}'],
            ["Discounts", f'{summary["discount"]:.2f}'],
            ["Tax", f'{summary["tax"]:.2f}'],
            ["Gross profit", f'{summary["profit"]:.2f}'],
        ] + [[f"Payments — {m}", f"{v:.2f}"] for m, v in summary["by_method"].items()]
        return _export_or_render(
            request, context={"summary": summary, "day": day},
            template="reports/daily_sales.html",
            title=f"Daily sales — {day}", headers=headers, rows=rows,
            filename=f"daily-sales-{day}",
        )


class ProfitView(ManagerUpMixin, View):
    def get(self, request):
        start, end = date_range_from_request(request)
        group_by = request.GET.get("group_by", "day")
        if group_by not in ("day", "product", "category", "supplier"):
            group_by = "day"
        report = services.profit_report(start, end, group_by)
        headers = [group_by.title(), "Qty", "Revenue", "Cost", "Discount", "Profit"]
        rows = [
            [r["key"], r["qty"], f'{r["revenue"]:.2f}', f'{r["cost"]:.2f}',
             f'{r["discount"]:.2f}', f'{r["profit"]:.2f}']
            for r in report["rows"]
        ]
        totals = ["TOTAL", sum(r["qty"] for r in report["rows"]),
                  f'{sum(r["revenue"] for r in report["rows"]):.2f}',
                  f'{sum(r["cost"] for r in report["rows"]):.2f}',
                  f'{sum(r["discount"] for r in report["rows"]):.2f}',
                  f'{report["gross_profit"] + report["return_reversals"]:.2f}']
        return _export_or_render(
            request, context={"report": report, "start": start, "end": end},
            template="reports/profit.html",
            title=f"Profit report {start} → {end} (by {group_by})",
            headers=headers, rows=rows, totals_row=totals,
            filename=f"profit-{start}-{end}-{group_by}",
        )


class BestSellersView(ManagerUpMixin, View):
    def get(self, request):
        start, end = date_range_from_request(request)
        rows_qs = services.best_sellers(start, end, limit=50)
        headers = ["Product", "Type", "Qty sold", "Revenue"]
        rows = [
            [r["product__title"], r["product__type"], r["qty"], f'{r["revenue"]:.2f}']
            for r in rows_qs
        ]
        return _export_or_render(
            request, context={"rows": rows_qs, "start": start, "end": end},
            template="reports/best_sellers.html",
            title=f"Best sellers {start} → {end}",
            headers=headers, rows=rows, filename=f"best-sellers-{start}-{end}",
        )


class DeadStockView(ManagerUpMixin, View):
    def get(self, request):
        days = int(request.GET.get("days", 90) or 90)
        products = services.dead_stock(days)
        headers = ["Product", "SKU", "Category", "Stock", "Cost value"]
        rows = [
            [p.title, p.sku, p.category.name if p.category else "",
             p.current_stock, f"{p.cost_price * p.current_stock:.2f}"]
            for p in products
        ]
        return _export_or_render(
            request, context={"products": products, "days": days},
            template="reports/dead_stock.html",
            title=f"Dead stock (no sale in {days} days)",
            headers=headers, rows=rows, filename=f"dead-stock-{days}d",
        )


class AgingView(ManagerUpMixin, View):
    def get(self, request):
        report = aging_report()
        headers = ["Customer", "Current (≤30d)", "31–60d", "61–90d", "90+d", "Total due"]
        rows = [
            [r["customer"].name, f'{r["current"]:.2f}', f'{r["days30"]:.2f}',
             f'{r["days60"]:.2f}', f'{r["days90"]:.2f}', f'{r["total"]:.2f}']
            for r in report
        ]
        totals = [
            "TOTAL", f'{sum(r["current"] for r in report):.2f}',
            f'{sum(r["days30"] for r in report):.2f}',
            f'{sum(r["days60"] for r in report):.2f}',
            f'{sum(r["days90"] for r in report):.2f}',
            f'{sum(r["total"] for r in report):.2f}',
        ]
        return _export_or_render(
            request, context={"report": report},
            template="reports/aging.html",
            title="Receivables aging", headers=headers, rows=rows,
            totals_row=totals, filename="receivables-aging",
        )


class ExpenseListView(ManagerUpMixin, View):
    template_name = "reports/expenses.html"

    def get(self, request):
        start, end = date_range_from_request(request)
        expenses = services.expenses_in_period(start, end)
        headers = ["Date", "Category", "Description", "Amount"]
        rows = [
            [str(e.expense_date), e.get_category_display(), e.description, f"{e.amount:.2f}"]
            for e in expenses
        ]
        return _export_or_render(
            request, context={
                "expenses": expenses, "start": start, "end": end,
                "categories": Expense.Category.choices,
                "total": sum((e.amount for e in expenses), Decimal("0.00")),
                "today": timezone.localdate(),
            },
            template=self.template_name,
            title=f"Expenses {start} → {end}",
            headers=headers, rows=rows, filename=f"expenses-{start}-{end}",
        )

    def post(self, request):
        try:
            Expense.objects.create(
                category=request.POST.get("category", "other"),
                description=request.POST.get("description", "").strip(),
                amount=request.POST["amount"],
                expense_date=parse_date(request.POST.get("expense_date"), timezone.localdate()),
                user=request.user,
            )
            messages.success(request, "Expense recorded.")
        except Exception as exc:  # noqa: BLE001 — surface validation issues
            messages.error(request, f"Could not save expense: {exc}")
        return redirect("reports:expenses")
