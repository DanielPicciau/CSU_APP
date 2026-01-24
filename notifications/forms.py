"""
Django forms for the notifications app.
"""

from django import forms

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
        label="Reminder time (UK time)",
        help_text="All times are in UK time (GMT/BST)",
    )

    class Meta:
        model = ReminderPreferences
        fields = ["enabled", "time_of_day"]
