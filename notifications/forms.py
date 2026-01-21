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
            "class": "w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500",
        }),
        label="Enable daily reminders",
    )
    
    time_of_day = forms.TimeField(
        widget=forms.TimeInput(attrs={
            "class": "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
            "type": "time",
        }),
        label="Reminder time",
    )
    
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        widget=forms.Select(attrs={
            "class": "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
        }),
        label="Your timezone",
    )

    class Meta:
        model = ReminderPreferences
        fields = ["enabled", "time_of_day", "timezone"]
