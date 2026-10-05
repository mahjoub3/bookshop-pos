from django.contrib.auth.models import Group, User
from django.db import models


class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        CASHIER = "cashier", "Cashier"

    GROUPS = {
        Role.ADMIN: "Admin",
        Role.MANAGER: "Manager",
        Role.CASHIER: "Cashier",
    }

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)
    phone = models.CharField(max_length=40, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def sync_group(self):
        """Keep Django group membership aligned with the role field."""
        self.user.groups.clear()
        group, _ = Group.objects.get_or_create(name=self.GROUPS[self.role])
        self.user.groups.add(group)
        self.user.is_staff = self.role == self.Role.ADMIN
        self.user.save(update_fields=["is_staff"])
