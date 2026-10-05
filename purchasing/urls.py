from django.urls import path

from . import views

app_name = "purchasing"

urlpatterns = [
    path("", views.POListView.as_view(), name="po_list"),
    path("new/", views.POCreateView.as_view(), name="po_create"),
    path("<int:pk>/", views.PODetailView.as_view(), name="po_detail"),
    path("<int:pk>/status/", views.POStatusView.as_view(), name="po_status"),
    path("<int:pk>/receive/", views.POReceiveView.as_view(), name="po_receive"),
    path("supplier-return/", views.SupplierReturnView.as_view(), name="supplier_return"),
]
