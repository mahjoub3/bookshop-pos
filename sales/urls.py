from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("pos/", views.pos, name="pos"),
    path("pos/scan/", views.pos_scan, name="pos_scan"),
    path("pos/search/", views.pos_search, name="pos_search"),
    path("pos/add/<int:pk>/", views.pos_add, name="pos_add"),
    path("pos/update/<int:pk>/", views.pos_update, name="pos_update"),
    path("pos/remove/<int:pk>/", views.pos_remove, name="pos_remove"),
    path("pos/customer/", views.pos_set_customer, name="pos_set_customer"),
    path("pos/customer-search/", views.pos_customer_search, name="pos_customer_search"),
    path("pos/discount/", views.pos_set_discount, name="pos_set_discount"),
    path("pos/checkout/", views.pos_checkout, name="pos_checkout"),
    path("", views.SaleListView.as_view(), name="sale_list"),
    path("<int:pk>/", views.SaleDetailView.as_view(), name="sale_detail"),
    path("<int:pk>/receipt/", views.receipt, name="receipt"),
    path("<int:pk>/return/", views.sale_return, name="sale_return"),
]
