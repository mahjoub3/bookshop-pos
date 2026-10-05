from django.contrib import admin

from .models import Category, Product, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "balance", "is_active")
    search_fields = ("name", "phone")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title", "type", "sku", "barcode", "category",
        "cost_price", "sell_price", "current_stock", "is_active",
    )
    list_filter = ("type", "is_active", "category")
    search_fields = ("title", "author", "isbn", "sku", "barcode")
    readonly_fields = ("current_stock", "created_at", "updated_at")
