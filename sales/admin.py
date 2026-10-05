from django.contrib import admin

from .models import Payment, Return, Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("line_profit",)
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_no", "sale_date", "customer", "total",
        "payment_status", "amount_paid", "amount_due", "user",
    )
    list_filter = ("payment_status", "sale_date")
    search_fields = ("receipt_no", "customer__name")
    readonly_fields = ("sale_date",)
    inlines = [SaleItemInline, PaymentInline]


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ("sale", "product", "quantity", "unit_price", "refund_method", "return_date")
    list_filter = ("refund_method", "return_date")
