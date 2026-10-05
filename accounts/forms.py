from django import forms
from django.contrib.auth.models import User

from .models import Profile

INPUT = "w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 focus:border-indigo-500 focus:ring-indigo-500"


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": INPUT}), min_length=6)
    role = forms.ChoiceField(choices=Profile.Role.choices, widget=forms.Select(attrs={"class": INPUT}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": INPUT}))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password", "role", "phone", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": INPUT}),
            "first_name": forms.TextInput(attrs={"class": INPUT}),
            "last_name": forms.TextInput(attrs={"class": INPUT}),
            "email": forms.EmailInput(attrs={"class": INPUT}),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data["role"]
            profile.phone = self.cleaned_data["phone"]
            profile.save()
            profile.sync_group()
        return user


class UserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Profile.Role.choices, widget=forms.Select(attrs={"class": INPUT}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": INPUT}))
    new_password = forms.CharField(
        required=False, min_length=6,
        widget=forms.PasswordInput(attrs={"class": INPUT}),
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "phone", "new_password", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": INPUT}),
            "first_name": forms.TextInput(attrs={"class": INPUT}),
            "last_name": forms.TextInput(attrs={"class": INPUT}),
            "email": forms.EmailInput(attrs={"class": INPUT}),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and hasattr(self.instance, "profile"):
            self.fields["role"].initial = self.instance.profile.role
            self.fields["phone"].initial = self.instance.profile.phone

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])
        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data["role"]
            profile.phone = self.cleaned_data["phone"]
            profile.save()
            profile.sync_group()
        return user
