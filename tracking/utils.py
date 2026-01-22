"""
Utility helpers for tracking views and APIs.
"""

from datetime import timedelta

import pytz
from django.conf import settings
from django.utils import timezone

from subscriptions.entitlements import has_entitlement


def get_user_today(user):
    """Get today's date in the user's timezone."""
    user_tz = pytz.timezone(user.profile.default_timezone)
    return timezone.now().astimezone(user_tz).date()


def get_history_limit_days(user) -> int | None:
    """Return history limit in days for the user (None means unlimited)."""
    if has_entitlement(user, "history_unlimited"):
        return None
    return getattr(settings, "FREE_HISTORY_DAYS", 30)


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
