"""
Django forms for the notifications app.
"""

from django import forms

from accounts.forms import TIMEZONE_CHOICES
from .models import ReminderPreferences


class ReminderPreferencesForm(forms.ModelForm):
    """Form for updating reminder preferences."""

    enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-checkbox",
        }),
        label="Enable daily reminders",
    )
    
    time_of_day = forms.TimeField(
        widget=forms.TimeInput(attrs={
            "class": "form-input",
            "type": "time",
        }),
        label="Reminder time",
    )
    
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-input",
        }),
        label="Your timezone",
    )

    class Meta:
        model = ReminderPreferences
        fields = ["enabled", "time_of_day", "timezone"]
