from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView
from django.views.decorators.http import require_POST

from accounts.decorators import role_required, user_has_role
from catalog.models import Product
from core.utils import toast
from customers.models import Customer

from .models import Return, Sale
from . import services


# ---------------------------------------------------------------------------
# POS
# ---------------------------------------------------------------------------

def _pos_context(request):
    cart = services.get_cart(request)
    customer = None
    if cart.get("customer_id"):
        customer = Customer.objects.filter(pk=cart["customer_id"]).first()
    ctx = {
        "cart": cart,
        "lines": services.cart_lines(cart),
        "totals": services.cart_totals(cart),
        "customer": customer,
    }
    if customer:
        from customers.services import get_balance

        ctx["customer_balance"] = get_balance(customer)
    return ctx


@login_required
def pos(request):
    """The POS screen — cashiers, managers, admins."""
    return render(request, "sales/pos.html", _pos_context(request))


@require_POST
@login_required
def pos_scan(request):
    """Barcode / SKU / ISBN entry. hx-post -> refreshed cart partial."""
    code = request.POST.get("code", "").strip()
    cart = services.get_cart(request)
    if code:
        product = Product.objects.filter(
            Q(barcode=code) | Q(sku=code) | Q(isbn=code), is_active=True
        ).first()
        if product:
            services.cart_add(request, product, qty=1)
        else:
            return toast(
                render(request, "sales/partials/_pos_cart.html", _pos_context(request)),
                "error", f"No active product matches '{code}'.",
            )
    return render(request, "sales/partials/_pos_cart.html", _pos_context(request))


@login_required
def pos_search(request):
    """Live product search (title/ISBN/SKU/barcode). hx-get -> results partial."""
    q = request.GET.get("q", "").strip()
    results = Product.objects.none()
    if len(q) >= 2:
        results = Product.objects.filter(
            Q(title__icontains=q) | Q(isbn__icontains=q)
            | Q(sku__icontains=q) | Q(barcode__icontains=q) | Q(author__icontains=q),
            is_active=True,
        )[:10]
    return render(request, "sales/partials/_search_results.html", {"results": results})


@require_POST
@login_required
def pos_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    services.cart_add(request, product, qty=1)
    return render(request, "sales/partials/_pos_cart.html", _pos_context(request))


def _dec(value, default=None):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return default


@require_POST
@login_required
def pos_update(request, pk):
    services.cart_update(
        request, pk,
        qty=int(request.POST.get("qty") or 0) if request.POST.get("qty") else None,
        price=_dec(request.POST.get("price")),
        discount=_dec(request.POST.get("discount")),
    )
    return render(request, "sales/partials/_pos_cart.html", _pos_context(request))


@require_POST
@login_required
def pos_remove(request, pk):
    services.cart_remove(request, pk)
    return render(request, "sales/partials/_pos_cart.html", _pos_context(request))


@require_POST
@login_required
def pos_set_customer(request):
    cart = services.get_cart(request)
    customer_id = request.POST.get("customer_id")
    cart["customer_id"] = int(customer_id) if customer_id else None
    services.save_cart(request, cart)
    return render(request, "sales/partials/_pos_cart.html", _pos_context(request))


@require_POST
@login_required
def pos_set_discount(request):
    cart = services.get_cart(request)
    cart["discount"] = str(_dec(request.POST.get("discount"), Decimal("0.00")) or "0.00")
    services.save_cart(request, cart)
    return render(request, "sales/partials/_pos_cart.html", _pos_context(request))


@login_required
def pos_customer_search(request):
    """Customer autocomplete for the POS selector."""
    q = request.GET.get("q", "").strip()
    customers = Customer.objects.none()
    if len(q) >= 2:
        customers = Customer.objects.filter(
            Q(name__icontains=q) | Q(phone__icontains=q), is_active=True
        )[:10]
    return render(request, "sales/partials/_customer_results.html", {"customers": customers})


@require_POST
@login_required
def pos_checkout(request):
    cart = services.get_cart(request)
    customer = None
    if cart.get("customer_id"):
        customer = Customer.objects.filter(pk=cart["customer_id"], is_active=True).first()

    payments = []
    for method in ("cash", "card", "transfer"):
        amount = _dec(request.POST.get(f"pay_{method}"))
        if amount and amount > 0:
            payments.append({"method": method, "amount": amount})

    try:
        sale = services.create_sale(
            user=request.user, cart=cart, payments=payments, customer=customer,
            notes=request.POST.get("notes", ""),
            allow_negative_stock=request.POST.get("allow_negative") == "1"
            and user_has_role(request.user, "admin", "manager"),
            override_credit_limit=request.POST.get("override_credit") == "1"
            and user_has_role(request.user, "admin", "manager"),
        )
    except ValidationError as exc:
        ctx = _pos_context(request)
        ctx["checkout_error"] = True
        return toast(
            render(request, "sales/partials/_pos_cart.html", ctx),
            "error", "; ".join(exc.messages),
        )

    services.cart_clear(request)
    ctx = _pos_context(request)
    ctx["last_sale"] = sale
    return toast(
        render(request, "sales/partials/_pos_cart.html", ctx),
        "success", f"Sale {sale.receipt_no} saved.",
    )


# ---------------------------------------------------------------------------
# Sales list / detail / receipt / returns
# ---------------------------------------------------------------------------

from django.contrib.auth.mixins import LoginRequiredMixin


class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = "sales/sale_list.html"
    context_object_name = "sales"
    paginate_by = 25

    def get_queryset(self):
        qs = Sale.objects.select_related("customer", "user")
        # Cashiers only see their own sales.
        if not user_has_role(self.request.user, "admin", "manager"):
            qs = qs.filter(user=self.request.user)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(receipt_no__icontains=q) | Q(customer__name__icontains=q))
        status = self.request.GET.get("status")
        if status in ("paid", "partial", "credit"):
            qs = qs.filter(payment_status=status)
        return qs

    def get_template_names(self):
        if self.request.htmx:
            return ["sales/partials/_sale_table.html"]
        return [self.template_name]


class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = "sales/sale_detail.html"
    context_object_name = "sale"

    def get_queryset(self):
        return (
            Sale.objects.select_related("customer", "user")
            .prefetch_related("items__product", "payments", "returns")
        )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if (
            not user_has_role(request.user, "admin", "manager")
            and self.object.user_id != request.user.id
        ):
            messages.error(request, "You can only view your own sales.")
            return redirect("sales:sale_list")
        return self.render_to_response(self.get_context_data())


@login_required
def receipt(request, pk):
    """Clean, browser-printable receipt."""
    sale = get_object_or_404(
        Sale.objects.select_related("customer", "user").prefetch_related("items__product"),
        pk=pk,
    )
    return render(request, "sales/receipt.html", {"sale": sale})


@require_POST
@role_required("admin", "manager")
def sale_return(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    product = get_object_or_404(Product, pk=request.POST.get("product_id"))
    try:
        services.process_return(
            sale=sale, product=product,
            quantity=int(request.POST.get("quantity", 0)),
            refund_method=request.POST.get("refund_method", Return.RefundMethod.CREDIT),
            reason=request.POST.get("reason", ""), user=request.user,
        )
        messages.success(request, "Return processed and stock restocked.")
    except (ValidationError, ValueError) as exc:
        messages.error(request, "; ".join(getattr(exc, "messages", [str(exc)])))
    return redirect("sales:sale_detail", pk=pk)
