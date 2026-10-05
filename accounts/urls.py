from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.ShopLoginView.as_view(), name="login"),
    path("logout/", views.ShopLogoutView.as_view(), name="logout"),
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/new/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_edit"),
]
