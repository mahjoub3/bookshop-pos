from django import forms

INPUT = "w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 focus:border-indigo-500 focus:ring-indigo-500"


class AdjustmentForm(forms.Form):
    delta = forms.IntegerField(
        help_text="Positive to add stock, negative to remove.",
        widget=forms.NumberInput(attrs={"class": INPUT}),
    )
    txn_type = forms.ChoiceField(
        choices=[("adjustment", "Adjustment"), ("damage", "Damage / write-off")],
        widget=forms.Select(attrs={"class": INPUT}),
    )
    reason = forms.CharField(
        max_length=255, widget=forms.TextInput(attrs={"class": INPUT})
    )

    def clean_delta(self):
        delta = self.cleaned_data["delta"]
        if delta == 0:
            raise forms.ValidationError("Delta must not be zero.")
        return delta
