from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.management import call_command
from django.shortcuts import redirect, render
from django.views import View

from accounts.mixins import AdminRequiredMixin

from .models import Setting


class SettingsView(AdminRequiredMixin, View):
    """Shop settings — admin only."""

    template_name = "core/settings.html"

    def get(self, request):
        return render(request, self.template_name, {"settings_obj": Setting.load()})

    def post(self, request):
        s = Setting.load()
        s.shop_name = request.POST.get("shop_name", s.shop_name).strip() or s.shop_name
        s.address = request.POST.get("address", s.address)
        s.phone = request.POST.get("phone", s.phone)
        s.receipt_header = request.POST.get("receipt_header", s.receipt_header)
        s.receipt_footer = request.POST.get("receipt_footer", s.receipt_footer)
        s.currency = request.POST.get("currency", s.currency)[:8] or s.currency
        try:
            s.tax_rate = Decimal(request.POST.get("tax_rate") or s.tax_rate)
            s.low_stock_threshold = int(request.POST.get("low_stock_threshold") or s.low_stock_threshold)
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Invalid number in tax rate or threshold.")
            return redirect("core:settings")
        if request.FILES.get("logo"):
            s.logo = request.FILES["logo"]
        s.save()
        messages.success(request, "Settings saved.")
        return redirect("core:settings")


class RebuildStockCacheView(AdminRequiredMixin, View):
    """Trigger the stock-cache rebuild from the UI (admin only)."""

    def post(self, request):
        call_command("rebuild_stock_cache")
        messages.success(request, "Stock cache rebuilt from the ledger.")
        return redirect("core:settings")
