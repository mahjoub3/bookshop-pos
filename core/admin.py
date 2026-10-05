from django.contrib import admin

from .models import Setting


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Shop", {"fields": ("shop_name", "address", "phone", "logo", "currency")}),
        ("Receipt", {"fields": ("receipt_header", "receipt_footer", "tax_rate")}),
        ("Inventory", {"fields": ("low_stock_threshold",)}),
    )

    def has_add_permission(self, request):
        return not Setting.objects.exists()
