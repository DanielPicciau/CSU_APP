"""Tracking app configuration."""

from django.apps import AppConfig


class TrackingConfig(AppConfig):
    """Configuration for the tracking app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tracking"
    verbose_name = "CSU Tracking"
