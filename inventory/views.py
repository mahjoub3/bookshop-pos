from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from accounts.mixins import ManagerUpMixin, RoleRequiredMixin
from catalog.models import Product

from .forms import AdjustmentForm
from .models import InventoryTransaction
from . import services


class StockListView(RoleRequiredMixin, ListView):
    """Current stock per product (from the cached ledger sum)."""

    roles = ("admin", "manager", "cashier")
    model = Product
    template_name = "inventory/stock_list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related("category")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q))
        if self.request.GET.get("low") == "1":
            ids = [p.pk for p in qs if p.is_low_stock]
            qs = qs.filter(pk__in=ids)
        return qs.order_by("title")

    def get_template_names(self):
        if self.request.htmx:
            return ["inventory/partials/_stock_table.html"]
        return [self.template_name]


class LowStockView(ManagerUpMixin, ListView):
    template_name = "inventory/low_stock.html"
    context_object_name = "products"

    def get_queryset(self):
        return services.low_stock_products()


class ProductHistoryView(RoleRequiredMixin, ListView):
    """Per-product ledger history."""

    roles = ("admin", "manager", "cashier")
    template_name = "inventory/product_history.html"
    context_object_name = "txns"
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            InventoryTransaction.objects.filter(product=self.product)
            .select_related("user")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["product"] = self.product
        return ctx


class AdjustStockView(ManagerUpMixin, View):
    template_name = "inventory/adjust.html"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {
            "product": product, "form": AdjustmentForm(),
        })

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = AdjustmentForm(request.POST)
        if form.is_valid():
            try:
                services.adjust_stock(
                    product=product, delta=form.cleaned_data["delta"],
                    reason=form.cleaned_data["reason"], user=request.user,
                    txn_type=form.cleaned_data["txn_type"],
                )
                messages.success(request, f"Stock adjusted for '{product.title}'.")
                return redirect("inventory:product_history", pk=product.pk)
            except ValueError as exc:
                form.add_error(None, str(exc))
        return render(request, self.template_name, {"product": product, "form": form})


class StocktakeView(ManagerUpMixin, View):
    """Enter counted quantities for all active products; mismatches become
    stocktake corrections in the ledger."""

    template_name = "inventory/stocktake.html"

    def get(self, request):
        products = Product.objects.filter(is_active=True).order_by("title")
        return render(request, self.template_name, {"products": products})

    def post(self, request):
        counts = {}
        for key, value in request.POST.items():
            if key.startswith("count_") and value.strip() != "":
                try:
                    counts[int(key.removeprefix("count_"))] = int(value)
                except ValueError:
                    messages.error(request, f"Invalid count '{value}'.")
                    return redirect("inventory:stocktake")
        created = services.stocktake(counts=counts, user=request.user)
        messages.success(
            request,
            f"Stocktake complete: {len(created)} correction(s) posted."
            if created else "Stocktake complete: everything matched.",
        )
        return redirect("inventory:stock_list")
