from django.urls import path

from . import views

app_name = "customers"

urlpatterns = [
    path("", views.CustomerListView.as_view(), name="customer_list"),
    path("new/", views.CustomerCreateView.as_view(), name="customer_create"),
    path("<int:pk>/", views.CustomerDetailView.as_view(), name="customer_detail"),
    path("<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="customer_edit"),
    path("<int:pk>/pay/", views.RecordPaymentView.as_view(), name="record_payment"),
    path("<int:pk>/statement/", views.StatementPDFView.as_view(), name="statement"),
]
