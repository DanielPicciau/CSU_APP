"""
Django forms for the tracking app.
"""

from datetime import date

from django import forms
from django.conf import settings

from .models import DailyEntry


ITCH_CHOICES = [
    (0, "0 - None"),
    (1, "1 - Mild (present but not bothersome)"),
    (2, "2 - Moderate (bothersome but doesn't interfere with daily activities)"),
    (3, "3 - Severe (interferes with daily activities or sleep)"),
]

HIVE_CHOICES = [
    (0, "0 - None"),
    (1, "1 - Mild (less than 20 hives)"),
    (2, "2 - Moderate (20-50 hives)"),
    (3, "3 - Severe (more than 50 hives or large confluent areas)"),
]


class DailyEntryForm(forms.ModelForm):
    """Form for logging daily CSU entry."""

    itch_score = forms.ChoiceField(
        choices=ITCH_CHOICES,
        widget=forms.RadioSelect(attrs={
            "class": "sr-only peer",
        }),
        required=True,
        label="Itch Severity",
    )
    
    hive_count_score = forms.ChoiceField(
        choices=HIVE_CHOICES,
        widget=forms.RadioSelect(attrs={
            "class": "sr-only peer",
        }),
        required=True,
        label="Hive Count",
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "form-input form-textarea",
            "rows": 3,
            "placeholder": "Any additional notes about today... (optional)",
        }),
    )
    
    took_antihistamine = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-checkbox",
        }),
        label="I took antihistamine today",
    )

    class Meta:
        model = DailyEntry
        fields = ["itch_score", "hive_count_score", "notes", "took_antihistamine"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.entry_date = kwargs.pop("entry_date", date.today())
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.user
        instance.date = self.entry_date
        # Calculate combined score
        instance.itch_score = int(self.cleaned_data["itch_score"])
        instance.hive_count_score = int(self.cleaned_data["hive_count_score"])
        instance.score = instance.itch_score + instance.hive_count_score
        if commit:
            instance.save()
        return instance


class QuickScoreForm(forms.Form):
    """Quick form for just entering total score."""
    
    score = forms.IntegerField(
        min_value=0,
        max_value=settings.CSU_MAX_SCORE,
        widget=forms.NumberInput(attrs={
            "class": "form-input text-2xl text-center",
            "placeholder": "0-6",
        }),
    )
