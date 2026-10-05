from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_date", "category", "description", "amount", "user")
    list_filter = ("category", "expense_date")
    search_fields = ("description",)
