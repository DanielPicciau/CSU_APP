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
_INJECTION_DATE_CACHE = "_injection_date_cache"


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

    if biologic:
        weekday = biologic.last_injection_date.weekday()
        injection_date = biologic.last_injection_date
    else:
        weekday = None
        injection_date = None

    setattr(user, _INJECTION_WEEKDAY_CACHE, weekday)
    setattr(user, _INJECTION_DATE_CACHE, injection_date)
    return weekday


def get_injection_date(user):
    """
    Return the user's last_injection_date for their current biologic,
    or None if unavailable.

    Caches result on the user object alongside get_injection_weekday.
    """
    if hasattr(user, _INJECTION_DATE_CACHE):
        return getattr(user, _INJECTION_DATE_CACHE)
    # Calling get_injection_weekday populates both caches
    get_injection_weekday(user)
    return getattr(user, _INJECTION_DATE_CACHE, None)


def get_user_week_bounds(user, today=None):
    """
    Get the start and end dates for the user's current tracking week.

    For users with biologic injections, the 7-day tracking period is aligned
    so it starts on the same weekday as their injection.  For example, if the
    injection is on Thursday the week runs Thu→Wed and only days from Thursday
    onwards are expected to have entries.

    If the injection date is in the future the tracking week hasn't started yet,
    so we fall back to the rolling 7-day window ending today.

    For users without a biologic injection date, falls back to the standard
    rolling 7-day window ending today.

    Returns ``(week_start, week_end)`` tuple.
    """
    today = today or get_user_today(user)
    injection_weekday = get_injection_weekday(user)
    injection_date = get_injection_date(user)

    if injection_weekday is not None:
        # If the injection date is in the future, week hasn't started yet
        if injection_date and injection_date > today:
            return today - timedelta(days=6), today

        # How many days since the most recent occurrence of the injection weekday?
        days_since = (today.weekday() - injection_weekday) % 7
        week_start = today - timedelta(days=days_since)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    # Default: rolling 7-day window ending today
    return today - timedelta(days=6), today


def get_treatment_week_number(user, today=None) -> int | None:
    """
    Return the 1-based treatment week number since the last injection date.

    Week 1 = injection day through day 6 after injection.
    Week 2 = day 7 through day 13, etc.

    Returns None if the user has no biologic with a last_injection_date,
    or if the injection date is in the future (treatment hasn't started).

    Overflow is supported: if treatment cycle is 4 weeks but the user is
    on day 30, this returns 5 (week 5).
    """
    today = today or get_user_today(user)
    injection_date = get_injection_date(user)

    if injection_date is None:
        return None
    if injection_date > today:
        return None  # Injection hasn't happened yet

    days_since = (today - injection_date).days
    return (days_since // 7) + 1


def get_treatment_cycle_info(user, today=None) -> dict | None:
    """
    Return a dict describing the current treatment cycle status.

    Keys:
        week_number: int — current 1-based week (supports overflow beyond cycle)
        day_in_cycle: int — 1-based day count since injection
        expected_weeks: int | None — expected cycle length in weeks (e.g. 4)
        is_overflow: bool — True if current week exceeds expected cycle weeks
        injection_date: date — the last injection date

    Returns None when the user has no biologic injection date or the date
    is in the future.
    """
    today = today or get_user_today(user)
    injection_date = get_injection_date(user)

    if injection_date is None or injection_date > today:
        return None

    from accounts.models import UserMedication

    biologic = (
        UserMedication.objects.filter(
            user=user,
            medication_type="biologic",
            is_current=True,
            last_injection_date__isnull=False,
        )
        .only("last_injection_date", "injection_frequency")
        .first()
    )
    if biologic is None:
        return None

    days_since = (today - injection_date).days
    week_number = (days_since // 7) + 1

    freq_days = UserMedication.INJECTION_FREQUENCY_DAYS.get(
        biologic.injection_frequency
    )
    expected_weeks = (freq_days // 7) if freq_days else None
    is_overflow = (week_number > expected_weeks) if expected_weeks else False

    return {
        "week_number": week_number,
        "day_in_cycle": days_since + 1,
        "expected_weeks": expected_weeks,
        "is_overflow": is_overflow,
        "injection_date": injection_date,
    }


def get_aligned_week_bounds(user, today, week_num):
    """
    Return ``(week_start, week_end)`` for a numbered week offset.

    ``week_num=0`` is the current week, ``week_num=1`` is the previous week, etc.
    Uses injection-aligned weeks when available (and the injection date is not
    in the future), otherwise rolling 7-day windows.
    """
    injection_weekday = get_injection_weekday(user)
    injection_date = get_injection_date(user)

    if injection_weekday is not None and (injection_date is None or injection_date <= today):
        days_since = (today.weekday() - injection_weekday) % 7
        current_week_start = today - timedelta(days=days_since)
        week_start = current_week_start - timedelta(days=week_num * 7)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    week_end = today - timedelta(days=week_num * 7)
    week_start = week_end - timedelta(days=6)
    return week_start, week_end
