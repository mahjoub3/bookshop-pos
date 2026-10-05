from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/new/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("products/<int:pk>/edit/", views.ProductUpdateView.as_view(), name="product_edit"),
    path("products/<int:pk>/toggle/", views.ProductToggleActiveView.as_view(), name="product_toggle"),
    path("products/<int:pk>/barcode/", views.BarcodeLabelView.as_view(), name="product_barcode"),
    path("products/export/", views.ProductExportView.as_view(), name="product_export"),
    path("products/import/", views.ProductImportView.as_view(), name="product_import"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/new/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_edit"),
]
