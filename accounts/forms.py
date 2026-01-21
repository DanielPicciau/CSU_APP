"""
Django forms for the accounts app.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.password_validation import validate_password

import pytz

from .models import Profile

User = get_user_model()

# Common timezone choices (subset for better UX)
TIMEZONE_CHOICES = [
    ("America/New_York", "Eastern Time (US)"),
    ("America/Chicago", "Central Time (US)"),
    ("America/Denver", "Mountain Time (US)"),
    ("America/Los_Angeles", "Pacific Time (US)"),
    ("America/Phoenix", "Arizona (US)"),
    ("America/Anchorage", "Alaska"),
    ("Pacific/Honolulu", "Hawaii"),
    ("Europe/London", "London"),
    ("Europe/Paris", "Paris / Berlin"),
    ("Europe/Moscow", "Moscow"),
    ("Asia/Dubai", "Dubai"),
    ("Asia/Kolkata", "India"),
    ("Asia/Singapore", "Singapore"),
    ("Asia/Tokyo", "Tokyo"),
    ("Asia/Shanghai", "China"),
    ("Australia/Sydney", "Sydney"),
    ("Pacific/Auckland", "New Zealand"),
]


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form with email field styling."""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
            "placeholder": "your@email.com",
            "autocomplete": "email",
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
            "placeholder": "••••••••",
            "autocomplete": "current-password",
        }),
    )


class RegisterForm(UserCreationForm):
    """Custom registration form."""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
            "placeholder": "your@email.com",
            "autocomplete": "email",
        }),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
            "placeholder": "••••••••",
            "autocomplete": "new-password",
        }),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
            "placeholder": "••••••••",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = User
        fields = ["email", "password1", "password2"]


class ProfileForm(forms.ModelForm):
    """Form for updating user profile."""

    default_timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        widget=forms.Select(attrs={
            "class": "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
        }),
    )

    class Meta:
        model = Profile
        fields = ["default_timezone"]
