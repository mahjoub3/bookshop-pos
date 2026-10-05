from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("dj-admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("catalog/", include("catalog.urls")),
    path("inventory/", include("inventory.urls")),
    path("sales/", include("sales.urls")),
    path("purchasing/", include("purchasing.urls")),
    path("customers/", include("customers.urls")),
    path("reports/", include("reports.urls")),
    path("settings/", include("core.urls")),
    path("", include("dashboard.urls")),
]

from django.conf import settings  # noqa: E402

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        urlpatterns = [path("__debug__/", include("debug_toolbar.urls"))] + urlpatterns
