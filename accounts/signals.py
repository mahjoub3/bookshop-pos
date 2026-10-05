from django.contrib.auth.models import User
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        role = Profile.Role.ADMIN if instance.is_superuser else Profile.Role.CASHIER
        Profile.objects.get_or_create(user=instance, defaults={"role": role})


@receiver(post_migrate)
def create_role_groups(sender, **kwargs):
    """Ensure the three role groups exist after every migrate."""
    if sender.name != "accounts":
        return
    from django.contrib.auth.models import Group

    for name in ("Admin", "Manager", "Cashier"):
        Group.objects.get_or_create(name=name)
