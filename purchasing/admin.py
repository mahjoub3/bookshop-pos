from django.contrib import admin

from .models import PurchaseOrder, PurchaseOrderItem


class ItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "status", "order_date", "received_date", "total")
    list_filter = ("status", "order_date")
    inlines = [ItemInline]
