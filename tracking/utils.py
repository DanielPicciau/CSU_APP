"""
Utility helpers for tracking views and APIs.
"""

from datetime import timedelta

import pytz
from django.conf import settings
from django.utils import timezone

from subscriptions.entitlements import has_entitlement

# Per-request cache attribute names (stored on user object)
_USER_TODAY_CACHE = "_user_today_cache"
_HISTORY_LIMIT_CACHE = "_history_limit_days_cache"
_INJECTION_WEEKDAY_CACHE = "_injection_weekday_cache"


def get_user_today(user):
    """
    Get today's date in the user's timezone.
    
    Caches result on the user object to avoid repeated profile lookups.
    """
    if hasattr(user, _USER_TODAY_CACHE):
        return getattr(user, _USER_TODAY_CACHE)
    
    user_tz = pytz.timezone(user.profile.default_timezone)
    today = timezone.now().astimezone(user_tz).date()
    setattr(user, _USER_TODAY_CACHE, today)
    return today


def get_history_limit_days(user) -> int | None:
    """
    Return history limit in days for the user (None means unlimited).
    
    Caches result on the user object to avoid repeated entitlement checks.
    """
    if hasattr(user, _HISTORY_LIMIT_CACHE):
        return getattr(user, _HISTORY_LIMIT_CACHE)
    
    if has_entitlement(user, "history_unlimited"):
        limit = None
    else:
        limit = getattr(settings, "FREE_HISTORY_DAYS", 30)
    
    setattr(user, _HISTORY_LIMIT_CACHE, limit)
    return limit


def get_history_start_date(user, today=None):
    """Return earliest date accessible for user history (or None if unlimited)."""
    limit_days = get_history_limit_days(user)
    if limit_days is None:
        return None
    today = today or get_user_today(user)
    return today - timedelta(days=limit_days - 1)


def apply_history_limit(queryset, user, today=None):
    """Apply the free history window filter to a queryset."""
    history_start = get_history_start_date(user, today=today)
    if history_start:
        return queryset.filter(date__gte=history_start)
    return queryset


def enforce_history_range(user, start_date, end_date, today=None):
    """
    Validate and normalize a date range against the user's history access.

    Raises PermissionError if the range is outside the allowed history window.
    """
    today = today or get_user_today(user)
    if end_date > today:
        end_date = today
    if start_date > end_date:
        raise ValueError("start_date_after_end_date")
    history_start = get_history_start_date(user, today=today)
    if history_start and start_date < history_start:
        raise PermissionError("history_limit_exceeded")
    return start_date, end_date, history_start


def get_injection_weekday(user) -> int | None:
    """
    Return the weekday (0=Mon, 6=Sun) of the user's biologic injection day,
    or None if the user has no current biologic with a last_injection_date.

    Caches result on the user object to avoid repeated DB lookups.
    """
    if hasattr(user, _INJECTION_WEEKDAY_CACHE):
        return getattr(user, _INJECTION_WEEKDAY_CACHE)

    from accounts.models import UserMedication

    biologic = (
        UserMedication.objects.filter(
            user=user,
            medication_type="biologic",
            is_current=True,
            last_injection_date__isnull=False,
        )
        .only("last_injection_date")
        .first()
    )

    weekday = biologic.last_injection_date.weekday() if biologic else None
    setattr(user, _INJECTION_WEEKDAY_CACHE, weekday)
    return weekday


def get_user_week_bounds(user, today=None):
    """
    Get the start and end dates for the user's current tracking week.

    For users with biologic injections, the 7-day tracking period is aligned
    so it starts on the same weekday as their injection.  For example, if the
    injection is on Thursday the week runs Thu→Wed and only days from Thursday
    onwards are expected to have entries.

    For users without a biologic injection date, falls back to the standard
    rolling 7-day window ending today.

    Returns ``(week_start, week_end)`` tuple.
    """
    today = today or get_user_today(user)
    injection_weekday = get_injection_weekday(user)

    if injection_weekday is not None:
        # How many days since the most recent occurrence of the injection weekday?
        days_since = (today.weekday() - injection_weekday) % 7
        week_start = today - timedelta(days=days_since)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    # Default: rolling 7-day window ending today
    return today - timedelta(days=6), today


def get_aligned_week_bounds(user, today, week_num):
    """
    Return ``(week_start, week_end)`` for a numbered week offset.

    ``week_num=0`` is the current week, ``week_num=1`` is the previous week, etc.
    Uses injection-aligned weeks when available, otherwise rolling 7-day
    windows.
    """
    injection_weekday = get_injection_weekday(user)

    if injection_weekday is not None:
        days_since = (today.weekday() - injection_weekday) % 7
        current_week_start = today - timedelta(days=days_since)
        week_start = current_week_start - timedelta(days=week_num * 7)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    week_end = today - timedelta(days=week_num * 7)
    week_start = week_end - timedelta(days=6)
    return week_start, week_end
