"""
URL routes for accounts app (template views).
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("delete-account/", views.delete_account_view, name="delete_account"),
    path("privacy/", views.privacy_view, name="privacy"),
]
