from django.contrib import admin

from .models import Customer, CustomerPayment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "credit_limit", "is_active")
    search_fields = ("name", "phone")
    list_filter = ("is_active",)


@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):
    list_display = ("customer", "amount", "method", "payment_date", "user")
    list_filter = ("method", "payment_date")
