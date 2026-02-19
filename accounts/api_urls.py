"""
API URL routes for accounts app.
"""

from django.urls import path

from . import api_views

app_name = "accounts_api"

urlpatterns = [
    path("register/", api_views.RegisterAPIView.as_view(), name="register"),
    path("me/", api_views.UserDetailAPIView.as_view(), name="me"),
    path("entitlements/", api_views.EntitlementsAPIView.as_view(), name="entitlements"),
    path("profile/", api_views.ProfileUpdateAPIView.as_view(), name="profile"),
    path("password/change/", api_views.PasswordChangeAPIView.as_view(), name="password_change"),
    path("injection/record/", api_views.RecordInjectionAPIView.as_view(), name="record_injection"),
]
