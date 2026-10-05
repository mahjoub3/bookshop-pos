from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.SettingsView.as_view(), name="settings"),
    path("rebuild-stock-cache/", views.RebuildStockCacheView.as_view(), name="rebuild_stock_cache"),
]
