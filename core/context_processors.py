"""
Template context processors for the CSU Tracker.
"""

from django.conf import settings


def pwa_context(request):
    """Add PWA-related context variables to all templates."""
    context = {
        "VAPID_PUBLIC_KEY": settings.VAPID_PUBLIC_KEY,
        "CSU_MAX_SCORE": settings.CSU_MAX_SCORE,
        "show_consent_banner": False,
    }

    if request.user.is_authenticated:
        try:
            # Show banner if user hasn't given explicit privacy consent
            context["show_consent_banner"] = not request.user.profile.privacy_consent_given
        except Exception:
            pass
            
    return context
