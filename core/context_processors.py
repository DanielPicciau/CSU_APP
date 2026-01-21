"""
Template context processors for the CSU Tracker.
"""

from django.conf import settings


def pwa_context(request):
    """Add PWA-related context variables to all templates."""
    return {
        "VAPID_PUBLIC_KEY": settings.VAPID_PUBLIC_KEY,
        "CSU_MAX_SCORE": settings.CSU_MAX_SCORE,
    }
