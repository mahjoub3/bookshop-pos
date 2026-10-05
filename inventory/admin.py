from django.contrib import admin

from .models import InventoryTransaction


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "txn_type", "quantity_delta", "unit_cost", "user")
    list_filter = ("txn_type", "created_at")
    search_fields = ("product__title", "note")
    readonly_fields = ("created_at",)

    def has_change_permission(self, request, obj=None):
        return False  # append-only ledger

    def has_delete_permission(self, request, obj=None):
        return False
