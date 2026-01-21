"""
Django forms for the accounts app.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password

import pytz

from .models import Profile, SCORE_SCALE_CHOICES

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

    display_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Your name (optional)",
        }),
        label="Display Name",
    )
    
    default_timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-input",
        }),
        label="Timezone",
    )
    
    preferred_score_scale = forms.ChoiceField(
        choices=SCORE_SCALE_CHOICES,
        widget=forms.RadioSelect(attrs={
            "class": "radio-card__input",
        }),
        label="Preferred Score Input",
    )

    class Meta:
        model = Profile
        fields = ["display_name", "default_timezone", "preferred_score_scale"]


class CustomPasswordChangeForm(PasswordChangeForm):
    """Styled password change form."""
    
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Enter current password",
            "autocomplete": "current-password",
        }),
    )
    
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Enter new password",
            "autocomplete": "new-password",
        }),
    )
    
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Confirm new password",
            "autocomplete": "new-password",
        }),
    )


class DeleteAccountForm(forms.Form):
    """Form for confirming account deletion."""
    
    confirm_email = forms.EmailField(
        label="Confirm Email",
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "Enter your email to confirm",
        }),
        help_text="Type your email address to confirm account deletion.",
    )
    
    understand = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            "class": "form-checkbox",
        }),
        label="I understand this action is irreversible and all my data will be permanently deleted.",
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_confirm_email(self):
        email = self.cleaned_data.get("confirm_email")
        if email != self.user.email:
            raise forms.ValidationError("Email does not match your account email.")
        return email
