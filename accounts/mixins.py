from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .decorators import user_has_role


class RoleRequiredMixin(LoginRequiredMixin):
    """CBV mixin — subclass and set `roles = ("admin", "manager")`."""

    roles: tuple = ()

    def dispatch(self, request, *args, **kwargs):
        if not user_has_role(request.user, *self.roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    roles = ("admin",)


class ManagerUpMixin(RoleRequiredMixin):
    roles = ("admin", "manager")
