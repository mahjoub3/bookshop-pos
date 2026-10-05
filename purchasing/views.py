from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.mixins import ManagerUpMixin
from catalog.models import Product, Supplier

from .models import PurchaseOrder, PurchaseOrderItem
from . import services


class POListView(ManagerUpMixin, ListView):
    model = PurchaseOrder
    template_name = "purchasing/po_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related("supplier", "created_by")
        status = self.request.GET.get("status")
        if status in ("draft", "ordered", "received", "cancelled"):
            qs = qs.filter(status=status)
        return qs


class POCreateView(ManagerUpMixin, View):
    """Create a PO with line items posted as parallel arrays:
    product_id[], quantity[], unit_cost[]."""

    template_name = "purchasing/po_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "suppliers": Supplier.objects.filter(is_active=True),
            "products": Product.objects.filter(is_active=True).order_by("title"),
        })

    def post(self, request):
        supplier = get_object_or_404(Supplier, pk=request.POST.get("supplier"))
        product_ids = request.POST.getlist("product_id")
        quantities = request.POST.getlist("quantity")
        costs = request.POST.getlist("unit_cost")
        if not product_ids:
            messages.error(request, "Add at least one line item.")
            return redirect("purchasing:po_create")
        try:
            with transaction.atomic():
                po = PurchaseOrder.objects.create(
                    supplier=supplier,
                    status=request.POST.get("action") == "order"
                    and PurchaseOrder.Status.ORDERED or PurchaseOrder.Status.DRAFT,
                    notes=request.POST.get("notes", ""),
                    created_by=request.user,
                )
                for pid, qty, cost in zip(product_ids, quantities, costs):
                    product = Product.objects.get(pk=pid, is_active=True)
                    PurchaseOrderItem.objects.create(
                        po=po, product=product,
                        quantity_ordered=int(qty),
                        unit_cost=Decimal(cost),
                    )
                po.recompute_total()
        except (Product.DoesNotExist, ValueError, InvalidOperation) as exc:
            messages.error(request, f"Could not create PO: {exc}")
            return redirect("purchasing:po_create")
        messages.success(request, f"PO-{po.pk} created.")
        return redirect("purchasing:po_detail", pk=po.pk)


class PODetailView(ManagerUpMixin, DetailView):
    model = PurchaseOrder
    template_name = "purchasing/po_detail.html"
    context_object_name = "po"

    def get_queryset(self):
        return PurchaseOrder.objects.select_related("supplier", "created_by") \
            .prefetch_related("items__product")


class POStatusView(ManagerUpMixin, View):
    """Mark ordered / cancel."""

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        action = request.POST.get("action")
        if action == "order" and po.status == PurchaseOrder.Status.DRAFT:
            po.status = PurchaseOrder.Status.ORDERED
        elif action == "cancel" and po.status != PurchaseOrder.Status.RECEIVED:
            po.status = PurchaseOrder.Status.CANCELLED
        po.save(update_fields=["status"])
        messages.success(request, f"PO-{po.pk} is now {po.get_status_display()}.")
        return redirect("purchasing:po_detail", pk=pk)


class POReceiveView(ManagerUpMixin, View):
    template_name = "purchasing/po_receive.html"

    def get(self, request, pk):
        po = get_object_or_404(
            PurchaseOrder.objects.prefetch_related("items__product"), pk=pk
        )
        return render(request, self.template_name, {"po": po})

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        receipts = {}
        for key, value in request.POST.items():
            if key.startswith("receive_") and value.strip():
                try:
                    qty = int(value)
                    if qty > 0:
                        receipts[int(key.removeprefix("receive_"))] = qty
                except ValueError:
                    pass
        if not receipts:
            messages.error(request, "Enter at least one quantity to receive.")
            return redirect("purchasing:po_receive", pk=pk)
        try:
            services.receive_po(po=po, receipts=receipts, user=request.user)
            messages.success(request, "Stock received, costs updated to last cost.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("purchasing:po_receive", pk=pk)
        return redirect("purchasing:po_detail", pk=pk)


class SupplierReturnView(ManagerUpMixin, View):
    template_name = "purchasing/supplier_return.html"

    def get(self, request):
        return render(request, self.template_name, {
            "suppliers": Supplier.objects.filter(is_active=True),
            "products": Product.objects.filter(is_active=True).order_by("title"),
        })

    def post(self, request):
        try:
            services.return_to_supplier(
                supplier=get_object_or_404(Supplier, pk=request.POST.get("supplier")),
                product=get_object_or_404(Product, pk=request.POST.get("product")),
                quantity=int(request.POST.get("quantity", 0)),
                unit_cost=Decimal(request.POST.get("unit_cost", "0")),
                reason=request.POST.get("reason", ""), user=request.user,
            )
            messages.success(request, "Return to supplier recorded.")
        except (ValidationError, ValueError, InvalidOperation) as exc:
            messages.error(request, "; ".join(getattr(exc, "messages", [str(exc)])))
            return redirect("purchasing:supplier_return")
        return redirect("purchasing:po_list")
