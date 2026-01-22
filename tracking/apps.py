"""Tracking app configuration."""

from django.apps import AppConfig


class TrackingConfig(AppConfig):
    """Configuration for the tracking app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tracking"
    verbose_name = "CSU Tracking"

    def ready(self):
        """Set up signals when app is ready."""
        # Import here to avoid circular imports
        try:
            from core.cache import setup_cache_invalidation_signals
            setup_cache_invalidation_signals()
        except ImportError:
            pass  # Cache module not available
