from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.StockListView.as_view(), name="stock_list"),
    path("low-stock/", views.LowStockView.as_view(), name="low_stock"),
    path("stocktake/", views.StocktakeView.as_view(), name="stocktake"),
    path("product/<int:pk>/history/", views.ProductHistoryView.as_view(), name="product_history"),
    path("product/<int:pk>/adjust/", views.AdjustStockView.as_view(), name="adjust"),
]
