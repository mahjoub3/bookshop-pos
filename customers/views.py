from datetime import datetime

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import ManagerUpMixin, RoleRequiredMixin
from core.utils import parse_date

from .forms import CustomerForm, CustomerPaymentForm
from .models import Customer
from . import services


class CustomerListView(RoleRequiredMixin, ListView):
    roles = ("admin", "manager", "cashier")
    model = Customer
    template_name = "customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 25

    def get_queryset(self):
        qs = Customer.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            from django.db.models import Q

            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q))
        return qs

    def get_template_names(self):
        if self.request.htmx:
            return ["customers/partials/_customer_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["balances"] = {
            c.pk: services.get_balance(c) for c in ctx["customers"]
        }
        return ctx


class CustomerCreateView(ManagerUpMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:customer_list")

    def form_valid(self, form):
        messages.success(self.request, "Customer saved.")
        return super().form_valid(form)


class CustomerUpdateView(ManagerUpMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:customer_list")

    def form_valid(self, form):
        messages.success(self.request, "Customer updated.")
        return super().form_valid(form)


class CustomerDetailView(RoleRequiredMixin, DetailView):
    roles = ("admin", "manager", "cashier")
    model = Customer
    template_name = "customers/customer_detail.html"
    context_object_name = "customer"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = self.object
        ctx["balance"] = services.get_balance(customer)
        ctx["sales"] = customer.sales.prefetch_related("items")[:25]
        ctx["payments"] = customer.payments.select_related("user")[:25]
        ctx["payment_form"] = CustomerPaymentForm(customer=customer)
        return ctx


class RecordPaymentView(ManagerUpMixin, View):
    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        form = CustomerPaymentForm(request.POST, customer=customer)
        if form.is_valid():
            try:
                services.record_payment(
                    customer=customer,
                    amount=form.cleaned_data["amount"],
                    method=form.cleaned_data["method"],
                    sale=form.cleaned_data.get("sale"),
                    note=form.cleaned_data.get("note", ""),
                    user=request.user,
                )
                messages.success(request, "Payment recorded.")
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        else:
            messages.error(request, "Invalid payment — check the amount.")
        return redirect("customers:customer_detail", pk=pk)


class StatementPDFView(RoleRequiredMixin, View):
    """Printable PDF customer statement (ReportLab)."""

    roles = ("admin", "manager", "cashier")

    def get(self, request, pk):
        from core.models import Setting
        from reports.pdf import customer_statement_pdf

        customer = get_object_or_404(Customer, pk=pk)
        start = parse_date(request.GET.get("start"))
        end = parse_date(request.GET.get("end"))
        lines = services.statement_lines(customer, start, end)
        pdf_bytes = customer_statement_pdf(
            settings_obj=Setting.load(), customer=customer, lines=lines,
            closing_balance=services.get_balance(customer),
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="statement-{customer.pk}-'
            f'{datetime.now():%Y%m%d}.pdf"'
        )
        return response
