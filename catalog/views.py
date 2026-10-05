import base64
import io

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from accounts.mixins import ManagerUpMixin, RoleRequiredMixin

from .forms import CSVImportForm, CategoryForm, ProductForm, SupplierForm
from .models import Category, Product, Supplier
from . import services


# --- Products ----------------------------------------------------------------

class ProductListView(RoleRequiredMixin, ListView):
    roles = ("admin", "manager", "cashier")
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        qs = Product.objects.select_related("category")
        q = self.request.GET.get("q", "").strip()
        if q:
            from django.db.models import Q

            qs = qs.filter(
                Q(title__icontains=q) | Q(isbn__icontains=q)
                | Q(sku__icontains=q) | Q(barcode__icontains=q) | Q(author__icontains=q)
            )
        ptype = self.request.GET.get("type")
        if ptype in ("book", "stationery"):
            qs = qs.filter(type=ptype)
        cat = self.request.GET.get("category")
        if cat:
            qs = qs.filter(category_id=cat)
        if self.request.GET.get("low") == "1":
            ids = [p.pk for p in qs if p.is_low_stock]
            qs = qs.filter(pk__in=ids)
        if self.request.GET.get("inactive") != "1":
            qs = qs.filter(is_active=True)
        return qs

    def get_template_names(self):
        if self.request.htmx:
            return ["catalog/partials/_product_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.filter(is_active=True)
        ctx["filters"] = self.request.GET
        return ctx


class ProductDetailView(RoleRequiredMixin, View):
    roles = ("admin", "manager", "cashier")

    def get(self, request, pk):
        product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
        txns = product.stock_transactions.select_related("user").order_by("-created_at")[:50]
        sales = (
            product.sale_items.select_related("sale")
            .order_by("-sale__sale_date")[:50]
        )
        return render(request, "catalog/product_detail.html", {
            "product": product, "txns": txns, "sale_items": sales,
        })


class ProductCreateView(ManagerUpMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"
    success_url = reverse_lazy("catalog:product_list")

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.title}' saved.")
        return super().form_valid(form)


class ProductUpdateView(ManagerUpMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"
    success_url = reverse_lazy("catalog:product_list")

    def form_valid(self, form):
        messages.success(self.request, "Product updated.")
        return super().form_valid(form)


class ProductToggleActiveView(ManagerUpMixin, View):
    """Soft delete / restore — never hard-delete a product."""

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.save(update_fields=["is_active"])
        state = "restored" if product.is_active else "deactivated"
        messages.success(request, f"'{product.title}' {state}.")
        return redirect("catalog:product_list")


class ProductExportView(ManagerUpMixin, View):
    def get(self, request):
        csv_text = services.products_to_csv(Product.objects.select_related("category"))
        response = HttpResponse(csv_text, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="products.csv"'
        return response


class ProductImportView(ManagerUpMixin, View):
    template_name = "catalog/import.html"

    def get(self, request):
        return render(request, self.template_name, {"form": CSVImportForm()})

    def post(self, request):
        form = CSVImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
        if "confirm" in request.POST:
            rows = request.session.pop("import_rows", None)
            if rows is None:
                messages.error(request, "Import session expired — upload the file again.")
                return redirect("catalog:product_import")
            created, updated, errors = services.import_products(rows, user=request.user)
            messages.success(request, f"Import done: {created} created, {updated} updated.")
            for err in errors:
                messages.warning(request, err)
            return redirect("catalog:product_list")
        rows, errors = services.parse_product_csv(form.cleaned_data["file"])
        request.session["import_rows"] = rows
        return render(request, self.template_name, {
            "form": form, "preview": rows[:50], "row_count": len(rows), "errors": errors,
        })


class BarcodeLabelView(RoleRequiredMixin, View):
    """Printable page with the product's Code128 barcode as PNG."""

    roles = ("admin", "manager", "cashier")

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        code = product.barcode or product.sku or product.isbn or str(product.pk)
        import barcode
        from barcode.writer import ImageWriter

        buf = io.BytesIO()
        barcode.Code128(code, writer=ImageWriter()).write(
            buf, options={"module_height": 12, "font_size": 8, "text_distance": 2}
        )
        png_b64 = base64.b64encode(buf.getvalue()).decode()
        return render(request, "catalog/barcode_label.html", {
            "product": product, "png_b64": png_b64, "code": code,
        })


# --- Categories --------------------------------------------------------------

class CategoryListView(ManagerUpMixin, ListView):
    model = Category
    template_name = "catalog/category_list.html"
    context_object_name = "categories"
    paginate_by = 50

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = CategoryForm()
        return ctx

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category saved.")
        else:
            messages.error(request, "Could not save category — check the form.")
        return redirect("catalog:category_list")


class CategoryUpdateView(ManagerUpMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "catalog/category_form.html"
    success_url = reverse_lazy("catalog:category_list")


# --- Suppliers ---------------------------------------------------------------

class SupplierListView(ManagerUpMixin, ListView):
    model = Supplier
    template_name = "catalog/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return qs


class SupplierCreateView(ManagerUpMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "catalog/supplier_form.html"
    success_url = reverse_lazy("catalog:supplier_list")

    def form_valid(self, form):
        messages.success(self.request, "Supplier saved.")
        return super().form_valid(form)


class SupplierUpdateView(ManagerUpMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "catalog/supplier_form.html"
    success_url = reverse_lazy("catalog:supplier_list")

    def form_valid(self, form):
        messages.success(self.request, "Supplier updated.")
        return super().form_valid(form)
