
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.ThrottledLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # User management
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),

    # Activate / deactivate account
    path(
        "users/<int:pk>/active/",
        views.toggle_active,
        name="toggle_active",
    ),

    # Change user role
    path(
        "users/<int:pk>/role/",
        views.change_role,
        name="change_role",
    ),

    # Change username
    path(
        "users/<int:pk>/change-username/",
        views.change_username,
        name="change_username",
    ),

    # Delete user
    path(
        "users/<int:pk>/delete/",
        views.delete_user,
        name="delete_user",
    ),

    # Reset user password
    path(
        "users/<int:pk>/reset-password/",
        views.reset_user_password,
        name="reset_user_password",
    ),
]
