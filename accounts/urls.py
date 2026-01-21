"""
URL routes for accounts app (template views).
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    
    # Account management
    path("profile/", views.profile_view, name="profile"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("delete-account/", views.delete_account_view, name="delete_account"),
    path("privacy/", views.privacy_view, name="privacy"),
    
    # Onboarding flow
    path("onboarding/", views.onboarding_welcome, name="onboarding_welcome"),
    path("onboarding/account/", views.onboarding_account, name="onboarding_account"),
    path("onboarding/name/", views.onboarding_name, name="onboarding_name"),
    path("onboarding/age/", views.onboarding_age, name="onboarding_age"),
    path("onboarding/gender/", views.onboarding_gender, name="onboarding_gender"),
    path("onboarding/diagnosis/", views.onboarding_diagnosis, name="onboarding_diagnosis"),
    # Treatment context (conditional steps)
    path("onboarding/medication/", views.onboarding_medication_status, name="onboarding_medication_status"),
    path("onboarding/medication/select/", views.onboarding_medication_select, name="onboarding_medication_select"),
    path("onboarding/medication/details/", views.onboarding_medication_details, name="onboarding_medication_details"),
    # Summary, consent, and completion
    path("onboarding/summary/", views.onboarding_summary, name="onboarding_summary"),
    path("onboarding/privacy/", views.onboarding_privacy, name="onboarding_privacy"),
    path("onboarding/reminders/", views.onboarding_reminders, name="onboarding_reminders"),
    path("onboarding/complete/", views.onboarding_complete, name="onboarding_complete"),
]
