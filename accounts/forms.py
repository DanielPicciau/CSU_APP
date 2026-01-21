"""
Django forms for the accounts app.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

import pytz

from .models import (
    Profile, 
    SCORE_SCALE_CHOICES, 
    GENDER_CHOICES, 
    CSU_DIAGNOSIS_CHOICES,
    MEDICATION_STATUS_CHOICES,
    COMMON_MEDICATIONS,
    INJECTION_FREQUENCY_CHOICES,
    UserMedication,
)

User = get_user_model()

# Common timezone choices (subset for better UX) - UK default
TIMEZONE_CHOICES = [
    ("Europe/London", "UK (GMT/BST)"),
    ("Europe/Dublin", "Ireland (GMT/IST)"),
    ("Europe/Paris", "Central Europe (CET/CEST)"),
    ("Europe/Berlin", "Germany (CET/CEST)"),
    ("Europe/Moscow", "Moscow (MSK)"),
    ("America/New_York", "US Eastern (ET)"),
    ("America/Chicago", "US Central (CT)"),
    ("America/Denver", "US Mountain (MT)"),
    ("America/Los_Angeles", "US Pacific (PT)"),
    ("America/Anchorage", "Alaska (AKT)"),
    ("Pacific/Honolulu", "Hawaii (HT)"),
    ("Asia/Dubai", "Dubai (GST)"),
    ("Asia/Kolkata", "India (IST)"),
    ("Asia/Singapore", "Singapore (SGT)"),
    ("Asia/Tokyo", "Japan (JST)"),
    ("Asia/Shanghai", "China (CST)"),
    ("Australia/Sydney", "Sydney (AEST/AEDT)"),
    ("Pacific/Auckland", "New Zealand (NZST/NZDT)"),
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


# =============================================================================
# ONBOARDING FORMS
# =============================================================================

class OnboardingAccountForm(forms.Form):
    """Account creation with personal details for onboarding."""
    
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-input form-input--onboarding",
            "placeholder": "First name",
            "autocomplete": "given-name",
            "autofocus": True,
        }),
        label="First name",
    )
    
    last_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            "class": "form-input form-input--onboarding",
            "placeholder": "Last name",
            "autocomplete": "family-name",
        }),
        label="Last name",
    )
    
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            "class": "form-input form-input--onboarding",
            "type": "date",
            "max": "",  # Will be set by JavaScript to today's date
        }),
        label="Date of birth",
        help_text="Used to keep your profile accurate over time.",
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-input form-input--onboarding",
            "placeholder": "your@email.com",
            "autocomplete": "email",
        }),
        label="Email",
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-input form-input--onboarding",
            "placeholder": "Create a password",
            "autocomplete": "new-password",
        }),
        label="Password",
        help_text="At least 12 characters with uppercase, lowercase, number, and special character.",
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            # Use generic error to prevent user enumeration
            raise forms.ValidationError(
                "Unable to create account with this email. Please try a different email "
                "or reset your password if you already have an account."
            )
        return email
    
    def clean_password(self):
        """Validate password using Django's AUTH_PASSWORD_VALIDATORS."""
        password = self.cleaned_data.get("password")
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password
    
    def clean_date_of_birth(self):
        """Validate date of birth is reasonable."""
        from datetime import date
        dob = self.cleaned_data.get("date_of_birth")
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 13:
                raise forms.ValidationError("You must be at least 13 years old to use this app.")
            if age > 120:
                raise forms.ValidationError("Please enter a valid date of birth.")
        return dob


class OnboardingNameForm(forms.Form):
    """Step: What's your name? (Legacy - now collected in account step)"""
    
    display_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-input form-input--onboarding",
            "placeholder": "Your first name",
            "autocomplete": "given-name",
            "autofocus": True,
        }),
        label="What should we call you?",
    )


class OnboardingAgeForm(forms.Form):
    """Step: What is your age?"""
    
    age = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=120,
        widget=forms.NumberInput(attrs={
            "class": "form-input form-input--onboarding",
            "placeholder": "Your age",
            "inputmode": "numeric",
            "autofocus": True,
        }),
        label="What is your age?",
    )


class OnboardingGenderForm(forms.Form):
    """Step: How do you describe your gender?"""
    
    gender = forms.ChoiceField(
        choices=[("", "")] + list(GENDER_CHOICES),
        required=False,
        widget=forms.RadioSelect(attrs={
            "class": "onboarding-radio__input",
        }),
        label="How do you describe your gender?",
    )


class OnboardingDiagnosisForm(forms.Form):
    """Step: Have you been diagnosed with CSU?"""
    
    csu_diagnosis = forms.ChoiceField(
        choices=[("", "")] + list(CSU_DIAGNOSIS_CHOICES),
        required=False,
        widget=forms.RadioSelect(attrs={
            "class": "onboarding-radio__input",
        }),
        label="Have you been diagnosed with Chronic Spontaneous Urticaria (CSU)?",
    )


# =============================================================================
# TREATMENT ONBOARDING FORMS
# Collects contextual metadata for trend visualization
# NOT medical advice - all fields optional
# =============================================================================

class OnboardingMedicationStatusForm(forms.Form):
    """Step: Have you been prescribed medication?"""
    
    has_prescribed_medication = forms.ChoiceField(
        choices=[("", "")] + list(MEDICATION_STATUS_CHOICES),
        required=False,
        widget=forms.RadioSelect(attrs={
            "class": "onboarding-radio__input",
        }),
        label="Have you been prescribed medication for this condition?",
    )


class OnboardingMedicationSelectForm(forms.Form):
    """Step: Select medications from list or add custom."""
    
    # Build choices from COMMON_MEDICATIONS
    MEDICATION_CHOICES = [(key, label) for key, label, _ in COMMON_MEDICATIONS]
    
    selected_medications = forms.MultipleChoiceField(
        choices=MEDICATION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            "class": "onboarding-checkbox__input",
        }),
        label="Which medications have you been prescribed?",
    )
    
    custom_medication = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-input form-input--onboarding",
            "placeholder": "Or enter a medication not listed above",
        }),
        label="Other medication",
    )


class OnboardingAntihistamineDetailsForm(forms.Form):
    """Step: Antihistamine dose and frequency (optional context)."""
    
    dose_amount = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-input form-input--onboarding form-input--inline",
            "placeholder": "e.g. 180",
            "inputmode": "decimal",
        }),
        label="Dose",
    )
    
    dose_unit = forms.ChoiceField(
        choices=[
            ("mg", "mg"),
            ("ml", "ml"),
            ("mcg", "mcg"),
        ],
        initial="mg",
        required=False,
        widget=forms.Select(attrs={
            "class": "form-input form-input--onboarding form-input--inline",
        }),
        label="Unit",
    )
    
    frequency_per_day = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={
            "class": "form-input form-input--onboarding form-input--inline",
            "placeholder": "e.g. 1",
            "inputmode": "numeric",
        }),
        label="Times per day",
    )


class OnboardingInjectionDetailsForm(forms.Form):
    """Step: Injection/biologic context for trend visualization."""
    
    last_injection_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-input form-input--onboarding",
            "type": "date",
        }),
        label="When was your last injection?",
    )
    
    injection_frequency = forms.ChoiceField(
        choices=[("", "Select frequency...")] + list(INJECTION_FREQUENCY_CHOICES),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-input form-input--onboarding",
        }),
        label="How often do you usually receive it?",
    )


# =============================================================================
# ONBOARDING COMPLETION FORMS
# Privacy consent, reminders, and transition to app
# =============================================================================

class OnboardingPrivacyConsentForm(forms.Form):
    """Step: Privacy consent and data transparency."""
    
    privacy_consent = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            "class": "onboarding-consent__input",
        }),
        label="I understand and agree to how my data will be used",
    )
    
    allow_analytics = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            "class": "onboarding-consent__input",
        }),
        label="Help improve the app with anonymous usage data (optional)",
    )


class OnboardingReminderForm(forms.Form):
    """Step: Daily reminder setup."""
    
    REMINDER_CHOICES = [
        ("yes", "Yes, remind me daily"),
        ("no", "No thanks, I'll remember"),
    ]
    
    # Timezone choices - UK first (default), then common ones
    TIMEZONE_CHOICES = [
        ("Europe/London", "UK (GMT/BST)"),
        ("Europe/Dublin", "Ireland (GMT/IST)"),
        ("Europe/Paris", "Central Europe (CET/CEST)"),
        ("Europe/Berlin", "Germany (CET/CEST)"),
        ("America/New_York", "US Eastern (ET)"),
        ("America/Chicago", "US Central (CT)"),
        ("America/Denver", "US Mountain (MT)"),
        ("America/Los_Angeles", "US Pacific (PT)"),
        ("America/Anchorage", "Alaska (AKT)"),
        ("Pacific/Honolulu", "Hawaii (HT)"),
        ("Australia/Sydney", "Sydney (AEST/AEDT)"),
        ("Asia/Tokyo", "Japan (JST)"),
        ("Asia/Singapore", "Singapore (SGT)"),
    ]
    
    enable_reminders = forms.ChoiceField(
        choices=REMINDER_CHOICES,
        required=False,
        widget=forms.RadioSelect(attrs={
            "class": "onboarding-radio__input",
        }),
        label="Would you like a daily reminder to log your symptoms?",
    )
    
    reminder_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            "class": "form-input form-input--onboarding",
            "type": "time",
        }),
        label="What time works best?",
        initial="20:00",
    )
    
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        required=False,
        initial="Europe/London",
        widget=forms.Select(attrs={
            "class": "form-input form-input--onboarding",
        }),
        label="Your timezone",
    )
