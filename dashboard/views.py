import json

from accounts.decorators import user_has_role
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from customers.services import overdue_customers
from inventory.services import low_stock_products
from reports import services as report_services
from sales.models import Sale


class HomeView(LoginRequiredMixin, View):
    template_name = "dashboard/home.html"

    def get(self, request):
        today = timezone.localdate()
        summary = report_services.daily_sales_summary(today)

        month_start = today.replace(day=1)
        top_sellers = report_services.best_sellers(month_start, today, limit=5)

        recent_sales = Sale.objects.select_related("customer", "user")
        if not user_has_role(request.user, "admin", "manager"):
            recent_sales = recent_sales.filter(user=request.user)
        recent_sales = recent_sales[:8]
        low_stock = low_stock_products()
        overdue = overdue_customers()

        chart = report_services.sales_chart_data(30)
        return render(request, self.template_name, {
            "summary": summary,
            "low_stock": low_stock[:10],
            "low_stock_count": len(low_stock),
            "overdue": overdue,
            "overdue_count": len(overdue),
            "top_sellers": top_sellers,
            "recent_sales": recent_sales,
            "chart_labels": json.dumps(chart["labels"]),
            "chart_data": json.dumps(chart["data"]),
        })
