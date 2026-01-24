"""
Entitlement resolution and helpers for premium feature gating.
"""

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from .models import EntitlementOverride, Subscription


FREE_ENTITLEMENTS = {
    "premium_access": False,
    "history_unlimited": False,
    "reports_advanced": False,
    "cloud_backup": False,
    "sharing": False,
    "scheduled_reports": False,
    "comparison_reports": False,
    "insights_ai": False,
    "priority_notifications": False,
    "calendar_sync": False,
    "widgets": False,
    "custom_themes": False,
    "achievements": False,
}

# Per-request cache attribute name (stored on user object)
_REQUEST_CACHE_ATTR = "_entitlements_cache"

PREMIUM_ENTITLEMENTS = {
    "premium_access": True,
    "history_unlimited": True,
    "reports_advanced": True,
    "cloud_backup": True,
    "sharing": True,
    "scheduled_reports": True,
    "comparison_reports": True,
    "insights_ai": True,
    "priority_notifications": True,
    "calendar_sync": True,
    "widgets": True,
    "custom_themes": True,
    "achievements": True,
}

m


def _cache_key(user_id: int) -> str:
    return f"entitlements:{user_id}"


def invalidate_entitlements_cache(user_id: int) -> None:
    """Clear cached entitlements for a user."""
    if user_id:
        cache.delete(_cache_key(user_id))


def _active_overrides(user_id: int):
    now = timezone.now()
    return EntitlementOverride.objects.filter(
        user_id=user_id,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))


def apply_overrides(entitlements: dict, user_id: int) -> dict:
    """Apply entitlement overrides for a user."""
    for override in _active_overrides(user_id):
        entitlements[override.entitlement_key] = override.value
    return entitlements


def resolve_entitlements(user) -> dict:
    """
    Resolve entitlements for a user.

    Premium is granted if the user has an active/trialing/grace subscription
    or is a superuser. Overrides are applied last.
    
    Uses per-request caching (stored on user object) to avoid repeated DB queries
    within the same request, plus global cache for cross-request performance.
    """
    if not user or not user.is_authenticated:
        return FREE_ENTITLEMENTS.copy()

    # Check per-request cache first (avoids DB hits within same request)
    if hasattr(user, _REQUEST_CACHE_ATTR):
        return getattr(user, _REQUEST_CACHE_ATTR)

    cache_key = _cache_key(user.id)
    if ENTITLEMENTS_CACHE_TTL > 0:
        cached = cache.get(cache_key)
        if cached:
            # Store in per-request cache too
            setattr(user, _REQUEST_CACHE_ATTR, cached)
            return cached

    entitlements = FREE_ENTITLEMENTS.copy()
    subscription = Subscription.objects.select_related("plan").filter(user=user).first()

    if user.is_superuser:
        entitlements = PREMIUM_ENTITLEMENTS.copy()
    elif subscription and subscription.is_premium:
        entitlements = PREMIUM_ENTITLEMENTS.copy()
        if subscription.plan and subscription.plan.entitlements_json:
            entitlements.update(subscription.plan.entitlements_json)

    entitlements = apply_overrides(entitlements, user.id)
    
    # Store in per-request cache
    setattr(user, _REQUEST_CACHE_ATTR, entitlements)
    
    if ENTITLEMENTS_CACHE_TTL > 0:
        cache.set(cache_key, entitlements, ENTITLEMENTS_CACHE_TTL)
    return entitlements


def has_entitlement(user, key: str) -> bool:
    """Check if a user has a specific entitlement."""
    return bool(resolve_entitlements(user).get(key, False))
