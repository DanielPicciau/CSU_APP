"""
Views for the accounts app (Django templates).
"""

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.utils import timezone

from .forms import (
    CustomAuthenticationForm,
    RegisterForm,
    ProfileForm,
    CustomPasswordChangeForm,
    DeleteAccountForm,
)


class CustomLoginView(LoginView):
    """Custom login view with styled form."""

    template_name = "accounts/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("home")


class CustomLogoutView(LogoutView):
    """Custom logout view."""

    next_page = reverse_lazy("accounts:login")


class RegisterView(CreateView):
    """User registration view."""

    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Welcome to CSU Tracker! Your account has been created.")
        return response


@login_required
def profile_view(request):
    """View and update user profile."""
    profile = request.user.profile
    
    # Get tracking stats for display
    from tracking.models import DailyEntry
    total_entries = DailyEntry.objects.filter(user=request.user).count()
    
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "accounts/profile_new.html", {
        "form": form,
        "profile": profile,
        "total_entries": total_entries,
    })


@login_required
def change_password_view(request):
    """Change user password."""
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed successfully!")
            return redirect("notifications:settings")
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, "accounts/change_password.html", {
        "form": form,
    })


@login_required
def delete_account_view(request):
    """Delete user account."""
    if request.method == "POST":
        form = DeleteAccountForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Your account has been permanently deleted.")
            return redirect("accounts:login")
    else:
        form = DeleteAccountForm(request.user)

    return render(request, "accounts/delete_account.html", {
        "form": form,
    })


@login_required
def privacy_view(request):
    """Privacy policy and data explanation."""
    profile = request.user.profile
    
    if request.method == "POST":
        # Handle privacy preference toggle
        allow_analytics = request.POST.get("allow_analytics") == "on"
        profile.allow_data_collection = allow_analytics
        profile.save()
        messages.success(request, "Privacy preferences updated.")
        return redirect("accounts:privacy")
    
    return render(request, "accounts/privacy.html", {
        "profile": profile,
    })
