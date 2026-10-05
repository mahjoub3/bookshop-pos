from django import forms

from .models import Customer, CustomerPayment

INPUT = "w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 focus:border-indigo-500 focus:ring-indigo-500"


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email", "address", "credit_limit", "notes", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT}),
            "phone": forms.TextInput(attrs={"class": INPUT}),
            "email": forms.EmailInput(attrs={"class": INPUT}),
            "address": forms.TextInput(attrs={"class": INPUT}),
            "credit_limit": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": 0}),
            "notes": forms.Textarea(attrs={"class": INPUT, "rows": 2}),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded"}),
        }


class CustomerPaymentForm(forms.ModelForm):
    class Meta:
        model = CustomerPayment
        fields = ["amount", "method", "sale", "note"]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0.01"}),
            "method": forms.Select(attrs={"class": INPUT}),
            "sale": forms.Select(attrs={"class": INPUT}),
            "note": forms.TextInput(attrs={"class": INPUT}),
        }

    def __init__(self, *args, customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        if customer:
            from sales.models import Sale

            self.fields["sale"].queryset = Sale.objects.filter(
                customer=customer, payment_status__in=("partial", "credit")
            ).order_by("-sale_date")
            self.fields["sale"].required = False

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount
