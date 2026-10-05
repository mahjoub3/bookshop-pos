from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("daily-sales/", views.DailySalesView.as_view(), name="daily_sales"),
    path("profit/", views.ProfitView.as_view(), name="profit"),
    path("best-sellers/", views.BestSellersView.as_view(), name="best_sellers"),
    path("dead-stock/", views.DeadStockView.as_view(), name="dead_stock"),
    path("aging/", views.AgingView.as_view(), name="aging"),
    path("expenses/", views.ExpenseListView.as_view(), name="expenses"),
]
