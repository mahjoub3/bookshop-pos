from django import forms

from .models import Category, Product, Supplier

INPUT = "w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 focus:border-indigo-500 focus:ring-indigo-500"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "parent", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT}),
            "parent": forms.Select(attrs={"class": INPUT}),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded"}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "phone", "email", "address", "notes", "balance", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT}),
            "phone": forms.TextInput(attrs={"class": INPUT}),
            "email": forms.EmailInput(attrs={"class": INPUT}),
            "address": forms.TextInput(attrs={"class": INPUT}),
            "notes": forms.Textarea(attrs={"class": INPUT, "rows": 2}),
            "balance": forms.NumberInput(attrs={"class": INPUT, "step": "0.01"}),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded"}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "type", "title", "isbn", "sku", "barcode", "author", "publisher",
            "category", "subject", "grade_level", "language", "unit", "pack_size",
            "cost_price", "sell_price", "reorder_level", "is_active",
        ]
        widgets = {
            field: forms.TextInput(attrs={"class": INPUT})
            for field in ("title", "isbn", "sku", "barcode", "author",
                          "publisher", "subject", "grade_level", "language")
        } | {
            "type": forms.Select(attrs={"class": INPUT}),
            "category": forms.Select(attrs={"class": INPUT}),
            "unit": forms.Select(attrs={"class": INPUT}),
            "pack_size": forms.NumberInput(attrs={"class": INPUT, "min": 1}),
            "cost_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": 0}),
            "sell_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": 0}),
            "reorder_level": forms.NumberInput(attrs={"class": INPUT, "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded"}),
        }


class CSVImportForm(forms.Form):
    file = forms.FileField(
        help_text="CSV headers: title, type, isbn, sku, barcode, author, publisher, "
                  "category, cost_price, sell_price, reorder_level, opening_stock"
    )
