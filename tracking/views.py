"""
Views for the tracking app (Django templates).
"""

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .models import DailyEntry
from .forms import DailyEntryForm, ITCH_CHOICES, HIVE_CHOICES
from .utils import (
    apply_history_limit,
    enforce_history_range,
    get_aligned_week_bounds,
    get_history_limit_days,
    get_history_start_date,
    get_user_today,
    get_user_week_bounds,
)
from core.cache import CacheManager, get_user_cache_key, CACHE_TIMEOUTS
from subscriptions.entitlements import has_entitlement
from .diagnostics import timed_section  # TEMP: performance profiling


@login_required
def home_view(request):
    """Home page - redirect to Today screen."""
    return redirect("tracking:today")


@login_required
def today_view(request):
    """Today screen - premium mobile-first experience."""
    from django.core.cache import cache

    with timed_section("today:get_user_today", request):
        today = get_user_today(request.user)
        user_id = request.user.id

    with timed_section("today:today_entry_query", request):
        # Try to serve today's entry from cache (warmed on login, invalidated on save)
        today_cache_key = get_user_cache_key(user_id, 'today_entry', str(today))
        today_entry = cache.get(today_cache_key)
        if today_entry is None:
            today_entry = DailyEntry.objects.filter(user=request.user, date=today).first()
            cache.set(today_cache_key, today_entry, CACHE_TIMEOUTS['dashboard_stats'])

    with timed_section("today:week_bounds+entries", request):
        # Determine the 7-day tracking window.
        week_start, week_end = get_user_week_bounds(request.user, today)

        # Try to serve recent entries from cache (warmed on login, invalidated on save)
        week_cache_key = get_user_cache_key(user_id, 'week_entries', str(week_start))
        recent_entries = cache.get(week_cache_key)
        if recent_entries is None:
            recent_entries = list(DailyEntry.objects.filter(
                user=request.user,
                date__gte=week_start,
                date__lte=min(week_end, today),
            ).only("date", "score").order_by("date"))
            cache.set(week_cache_key, recent_entries, CACHE_TIMEOUTS['dashboard_stats'])

    with timed_section("today:chart_data_build", request):
        # Build chart data with O(1) dict lookup instead of linear scan
        entry_by_date = {e.date: e for e in recent_entries}
        chart_data = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            is_future = day > today
            entry = entry_by_date.get(day)
            chart_data.append({
                "date": day,
                "score": entry.score if entry else None,
                "has_entry": entry is not None,
                "is_future": is_future,
            })

    with timed_section("today:uas7_calc", request):
        # Calculate UAS7 (sum of scores in this tracking week so far)
        uas7_score = sum(e.score for e in recent_entries)
        expected_days = min(7, (today - week_start).days + 1)
        uas7_complete = len(recent_entries) == expected_days and expected_days == 7

    with timed_section("today:adherence_30d_query", request):
        # Cache the 30-day adherence count (changes at most once/day)
        adherence_key = get_user_cache_key(user_id, 'adherence_30d', str(today))
        logged_in_30_days = cache.get(adherence_key)
        if logged_in_30_days is None:
            thirty_days_ago = today - timedelta(days=29)
            logged_in_30_days = DailyEntry.objects.filter(
                user=request.user,
                date__gte=thirty_days_ago,
                date__lte=today,
            ).count()
            cache.set(adherence_key, logged_in_30_days, CACHE_TIMEOUTS['dashboard_stats'])

    with timed_section("today:total_entries_query", request):
        # Cache total entries count
        total_key = get_user_cache_key(user_id, 'total_entries', '')
        total_entries = cache.get(total_key)
        if total_entries is None:
            total_entries = apply_history_limit(
                DailyEntry.objects.filter(user=request.user),
                request.user,
                today=today,
            ).count()
            cache.set(total_key, total_entries, CACHE_TIMEOUTS['dashboard_stats'])

    with timed_section("today:notification_check", request):
        # Check if notifications are actually enabled (not just if preferences exist)
        has_notification_setup = False
        if hasattr(request.user, 'reminder_preferences'):
            has_notification_setup = request.user.reminder_preferences.enabled

    with timed_section("today:template_render", request):
        response = render(request, "tracking/today.html", {
            "today": today,
            "today_entry": today_entry,
            "chart_data": chart_data,
            "uas7_score": uas7_score,
            "uas7_complete": uas7_complete,
            "logged_in_30_days": logged_in_30_days,
            "total_entries": total_entries,
            "has_notification_setup": has_notification_setup,
        })

    return response


@login_required
def log_entry_view(request, date_str=None):
    """Log or update a daily entry."""
    with timed_section("log:get_user_today+validate", request):
        user_today = get_user_today(request.user)
        
        if date_str:
            try:
                entry_date = date.fromisoformat(date_str)
            except ValueError:
                messages.error(request, "Invalid date format.")
                return redirect("tracking:today")
        else:
            entry_date = user_today
        
        # Prevent logging future dates
        if entry_date > user_today:
            messages.error(request, "Cannot log entries for future dates.")
            return redirect("tracking:today")

        history_start = get_history_start_date(request.user, today=user_today)
        if history_start and entry_date < history_start:
            messages.error(
                request,
                "Free tier access is limited to the last 30 days. Upgrade to edit older entries.",
            )
            return redirect("subscriptions:premium")

    with timed_section("log:existing_entry_query", request):
        # Check if entry exists (for update)
        existing_entry = DailyEntry.objects.filter(
            user=request.user,
            date=entry_date,
        ).first()
    
    # Handle structured quick mode (itch_score + hive_count_score)
    if request.method == "POST" and request.POST.get("structured_quick_mode"):
        try:
            itch = int(request.POST.get("itch_score", 0))
            hives = int(request.POST.get("hive_count_score", 0))
            
            # Validate ranges
            itch = max(0, min(3, itch))
            hives = max(0, min(3, hives))
            score = itch + hives
            
            if existing_entry:
                existing_entry.itch_score = itch
                existing_entry.hive_count_score = hives
                existing_entry.score = score
                existing_entry.save()
            else:
                DailyEntry.objects.create(
                    user=request.user,
                    date=entry_date,
                    score=score,
                    itch_score=itch,
                    hive_count_score=hives,
                )
            
            messages.success(request, "Score logged successfully!")
            return redirect("tracking:today")
        except (ValueError, TypeError):
            messages.error(request, "Invalid score values.")
            return redirect("tracking:today")
    
    # Handle legacy quick mode (score only, auto-split to itch/hives)
    if request.method == "POST" and request.POST.get("quick_mode"):
        score = int(request.POST.get("score", 0))
        itch = min(3, (score + 1) // 2)
        hives = min(3, score // 2)
        
        if existing_entry:
            existing_entry.itch_score = itch
            existing_entry.hive_count_score = hives
            existing_entry.score = itch + hives
            existing_entry.save()
        else:
            DailyEntry.objects.create(
                user=request.user,
                date=entry_date,
                score=score,
                itch_score=itch,
                hive_count_score=hives,
            )
        
        messages.success(request, "Score logged successfully!")
        return redirect("tracking:today")
    
    if request.method == "POST":
        form = DailyEntryForm(
            request.POST,
            instance=existing_entry,
            user=request.user,
            entry_date=entry_date,
        )
        if form.is_valid():
            form.save()
            action = "updated" if existing_entry else "logged"
            messages.success(request, f"Entry {action} successfully!")
            return redirect("tracking:today")
    else:
        form = DailyEntryForm(
            instance=existing_entry,
            user=request.user,
            entry_date=entry_date,
        )
    
    # Determine which template to use (check for new design preference)
    template = "tracking/log_entry_new.html"
    
    with timed_section("log:template_render", request):
        rendered = render(request, template, {
            "form": form,
            "entry_date": entry_date,
            "today": entry_date,
            "is_today": entry_date == user_today,
            "existing_entry": existing_entry,
            "editing": existing_entry is not None,
            "entry": existing_entry,
            "itch_choices": ITCH_CHOICES,
            "hive_choices": HIVE_CHOICES,
        })
    return rendered


@login_required
def history_view(request):
    """View entry history with filters and calendar view."""

    with timed_section("history:get_user_today+params", request):
        today = get_user_today(request.user)
        
        # Get filter parameters - default to 10 days for the new grid view
        try:
            days = max(1, min(365, int(request.GET.get("days", 10))))
        except (ValueError, TypeError):
            days = 10
        limit_days = get_history_limit_days(request.user)
        if limit_days is not None:
            days = min(days, limit_days)
        view = request.GET.get("view", "grid")  # Default to grid view
        show = request.GET.get("show", "all")
        min_score = request.GET.get("min_score")
        max_score = request.GET.get("max_score")
        antihistamine = request.GET.get("antihistamine")
        month_str = request.GET.get("month")
        
        start_date = today - timedelta(days=days - 1)
        
        history_start = get_history_start_date(request.user, today=today)

    with timed_section("history:main_entries_query", request):
        # Get all entries in range
        entries_query = DailyEntry.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today,
        )
        entries_query = apply_history_limit(entries_query, request.user, today=today)
    
    # Apply score filters at the DB layer
    if min_score:
        try:
            min_val = int(min_score)
            entries_query = entries_query.filter(score__gte=min_val)
        except (ValueError, TypeError):
            pass
    if max_score:
        try:
            max_val = int(max_score)
            entries_query = entries_query.filter(score__lte=max_val)
        except (ValueError, TypeError):
            pass
    if antihistamine:
        entries_query = entries_query.filter(took_antihistamine=True)
    
    entries = list(entries_query.only(
        "id",
        "date",
        "score",
        "itch_score",
        "hive_count_score",
        "took_antihistamine",
    ).order_by("-date"))

    with timed_section("history:list_data_loop", request):
        # Create entry lookup
        entry_by_date = {e.date: e for e in entries}
        
        # Build list data (all days in range)
        list_data = []
        entries_count = 0
        missing_count = 0
        
        for i in range(days):
            day = today - timedelta(days=i)
            entry = entry_by_date.get(day)
            is_missing = entry is None
            
            if is_missing:
                missing_count += 1
            else:
                entries_count += 1
            
            # Filter based on show parameter
            if show == "logged" and is_missing:
                continue
            if show == "missing" and not is_missing:
                continue
            
            list_data.append({
                "date": day,
                "entry": entry,
                "is_today": day == today,
                "is_missing": is_missing,
            })
        
        # Calculate adherence percentage
        adherence_pct = (entries_count / days * 100) if days > 0 else 0
    
    # Build calendar data for calendar view
    calendar_data = []
    if view == "calendar":
      with timed_section("history:calendar_build", request):
        # Determine which month to show
        if month_str:
            try:
                year, month = map(int, month_str.split("-"))
                current_month = date(year, month, 1)
            except ValueError:
                current_month = date(today.year, today.month, 1)
        else:
            current_month = date(today.year, today.month, 1)

        if history_start:
            earliest_month = date(history_start.year, history_start.month, 1)
            if current_month < earliest_month:
                current_month = earliest_month
        
        # Calculate prev/next months
        if current_month.month == 1:
            prev_month = date(current_month.year - 1, 12, 1)
        else:
            prev_month = date(current_month.year, current_month.month - 1, 1)
        
        if current_month.month == 12:
            next_month = date(current_month.year + 1, 1, 1)
        else:
            next_month = date(current_month.year, current_month.month + 1, 1)

        if history_start:
            earliest_month = date(history_start.year, history_start.month, 1)
            if prev_month < earliest_month:
                prev_month = None
        
        # Get first day of month and number of days
        first_day_weekday = current_month.weekday()  # Monday = 0
        # Adjust for Sunday start (0 = Sunday)
        first_day_weekday = (first_day_weekday + 1) % 7
        
        # Add empty cells for days before first of month
        for _ in range(first_day_weekday):
            calendar_data.append({"empty": True})
        
        # Get entries for this month
        month_end = (next_month - timedelta(days=1))
        month_entries_query = DailyEntry.objects.filter(
            user=request.user,
            date__gte=current_month,
            date__lte=month_end,
        )
        month_entries = apply_history_limit(
            month_entries_query,
            request.user,
            today=today,
        ).only(
            "date",
            "score",
            "itch_score",
            "hive_count_score",
        )
        month_entry_by_date = {e.date: e for e in month_entries}
        
        # Add days of the month
        day = current_month
        while day.month == current_month.month:
            is_future = day > today
            calendar_data.append({
                "date": day,
                "day": day.day,
                "entry": month_entry_by_date.get(day) if not is_future else None,
                "is_today": day == today,
                "future": is_future,
            })
            day += timedelta(days=1)

    with timed_section("history:has_older_entries", request):
        max_days = limit_days or 365
        has_older_entries = False
        if history_start:
            has_older_entries = DailyEntry.objects.filter(
                user=request.user,
                date__lt=history_start,
            ).exists()

    context = {
        "list_data": list_data,
        "calendar_data": calendar_data,
        "entries_count": entries_count,
        "missing_count": missing_count,
        "adherence_pct": adherence_pct,
        "days": days,
        "view": view,
        "today": today,
        "filter_show": show,
        "filter_min": min_score,
        "filter_max": max_score,
        "filter_antihistamine": antihistamine,
        "has_more": days < max_days,
        "next_days": min(days * 2, max_days),
        "history_limit_days": limit_days,
        "history_start": history_start,
        "history_limited": limit_days is not None,
        "has_older_entries": has_older_entries,
    }
    
    if view == "calendar":
        context.update({
            "current_month": current_month,
            "prev_month": prev_month,
            "next_month": next_month,
        })
    
    with timed_section("history:template_render", request):
        rendered = render(request, "tracking/history_premium.html", context)
    return rendered


@login_required
def insights_view(request):
    """View insights and analytics."""

    with timed_section("insights:get_user_today+params", request):
        today = get_user_today(request.user)
        
        # Get period parameter with safe parsing
        try:
            period = max(1, min(365, int(request.GET.get("period", 30))))
        except (ValueError, TypeError):
            period = 30
        limit_days = get_history_limit_days(request.user)
        if limit_days is not None:
            period = min(period, limit_days)
        start_date = today - timedelta(days=period - 1)

    with timed_section("insights:main_entries_query", request):
        # Get entries for period
        entries_query = DailyEntry.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=today,
        )
        entries = list(apply_history_limit(
            entries_query,
            request.user,
            today=today,
        ).only(
            "date",
            "score",
            "itch_score",
            "hive_count_score",
            "took_antihistamine",
        ).order_by("date"))

    with timed_section("insights:total_entries_count", request):
        logged_days = len(entries)
        missing_days = period - logged_days
        adherence_pct = (logged_days / period * 100) if period > 0 else 0
        adherence_offset = 327 - (327 * adherence_pct / 100)  # For SVG circle
        
        # Total entries count (non-judgmental lifetime metric)
        total_entries = apply_history_limit(
            DailyEntry.objects.filter(user=request.user),
            request.user,
            today=today,
        ).count()

    with timed_section("insights:avg_stats_calc", request):
        # Calculate averages
        if entries:
            avg_score = sum(e.score for e in entries) / len(entries)
            avg_itch = sum(e.itch_score for e in entries) / len(entries)
            avg_hives = sum(e.hive_count_score for e in entries) / len(entries)
            best_score = min(e.score for e in entries)
            worst_score = max(e.score for e in entries)
        else:
            avg_score = avg_itch = avg_hives = 0
            best_score = worst_score = "-"
        
        avg_score_pct = (avg_score / 6 * 100) if avg_score else 0
        avg_itch_pct = (avg_itch / 3 * 100) if avg_itch else 0
        avg_hives_pct = (avg_hives / 3 * 100) if avg_hives else 0
        
        # Antihistamine stats
        antihistamine_days = sum(1 for e in entries if e.took_antihistamine)
        antihistamine_pct = (antihistamine_days / logged_days * 100) if logged_days > 0 else 0

    with timed_section("insights:weekly_uas7_query", request):
        # Weekly UAS7 comparison (last 4 weeks) - Optimized: single query
        four_weeks_ago = today - timedelta(days=27)
        weekly_query = DailyEntry.objects.filter(
            user=request.user,
            date__gte=four_weeks_ago,
            date__lte=today,
        )
        all_weekly_entries = list(
            apply_history_limit(weekly_query, request.user, today=today).values("date", "score")
        )

    with timed_section("insights:weekly_loop_calc", request):
        # Build a lookup for entries by date
        entries_by_date = {e['date']: e['score'] for e in all_weekly_entries}
        
        weekly_scores = []
        for week_num in range(4):
            w_start, w_end = get_aligned_week_bounds(request.user, today, week_num)
            
            # Calculate from in-memory data instead of DB query
            week_uas7 = 0
            week_count = 0
            for day_offset in range(7):
                day = w_start + timedelta(days=day_offset)
                if day in entries_by_date:
                    week_uas7 += entries_by_date[day]
                    week_count += 1
            
            uas7 = week_uas7
            complete = week_count == 7
            
            # Calculate change from previous week
            change = None
            if week_num > 0 and weekly_scores:
                prev_uas7 = weekly_scores[-1]["uas7"]
                change = uas7 - prev_uas7
            
            weekly_scores.append({
                "week_start": w_start,
                "week_end": w_end,
                "uas7": uas7,
                "complete": complete,
                "change": change,
                "label": f"{week_num + 1}w ago",
            })

    with timed_section("insights:chart_building", request):
        # Build chart data
        chart_points = []
        chart_path = ""
        chart_area_path = ""
        chart_width = 300
        
        if entries:
            # Filter to only days with entries for clean chart
            padding_left = 25
            padding_right = 5
            usable_width = chart_width - padding_left - padding_right
            point_width = usable_width / max(len(entries) - 1, 1)
            
            for i, entry in enumerate(entries):
                x = round(padding_left + i * point_width, 1)
                y = round(130 - (entry.score / 6 * 105), 1)  # Invert Y axis
                chart_points.append({
                    "x": x,
                    "y": y,
                    "score": entry.score,
                    "date": entry.date.strftime("%b %d"),
                })
            
            if len(chart_points) > 1:
                # Build smooth bezier curve path for nicer line chart
                tension = 0.3  # Controls curve smoothness (0 = straight, 1 = very curved)
                path_parts = [f"M {chart_points[0]['x']} {chart_points[0]['y']}"]
                
                for i in range(1, len(chart_points)):
                    p0 = chart_points[max(i - 2, 0)]
                    p1 = chart_points[i - 1]
                    p2 = chart_points[i]
                    p3 = chart_points[min(i + 1, len(chart_points) - 1)]
                    
                    # Catmull-Rom to Bezier control points
                    cp1x = round(p1['x'] + (p2['x'] - p0['x']) * tension, 1)
                    cp1y = round(p1['y'] + (p2['y'] - p0['y']) * tension, 1)
                    cp2x = round(p2['x'] - (p3['x'] - p1['x']) * tension, 1)
                    cp2y = round(p2['y'] - (p3['y'] - p1['y']) * tension, 1)
                    
                    path_parts.append(
                        f"C {cp1x} {cp1y}, {cp2x} {cp2y}, {p2['x']} {p2['y']}"
                    )
                
                chart_path = " ".join(path_parts)
                
                # Build area path (line down to baseline, across, and close)
                chart_area_path = (
                    chart_path
                    + f" L {chart_points[-1]['x']} 130"
                    + f" L {chart_points[0]['x']} 130 Z"
                )
            elif len(chart_points) == 1:
                # Single point — just show it, no line needed
                chart_path = ""
                chart_area_path = ""
        
        # Compute average score Y position for SVG overlay line
        avg_score_y = round(130 - (avg_score / 6 * 105), 1) if avg_score else None

    with timed_section("insights:template_render", request):
        rendered = render(request, "tracking/insights.html", {
        "period": period,
        "today": today,
        "logged_days": logged_days,
        "missing_days": missing_days,
        "adherence_pct": adherence_pct,
        "adherence_offset": adherence_offset,
        "total_entries": total_entries,
        "avg_score": avg_score,
        "avg_itch": avg_itch,
        "avg_hives": avg_hives,
        "avg_score_pct": avg_score_pct,
        "avg_itch_pct": avg_itch_pct,
        "avg_hives_pct": avg_hives_pct,
        "best_score": best_score,
        "worst_score": worst_score,
        "antihistamine_days": antihistamine_days,
        "antihistamine_pct": antihistamine_pct,
        "weekly_scores": weekly_scores,
        "entries": entries,
        "chart_points": chart_points,
        "chart_path": chart_path,
        "chart_area_path": chart_area_path,
        "chart_width": chart_width,
        "avg_score_y": avg_score_y,
        "history_limit_days": limit_days,
        "history_limited": limit_days is not None,
    })

    return rendered


@login_required
def entry_detail_view(request, date_str):
    """View a specific entry's details."""
    try:
        entry_date = date.fromisoformat(date_str)
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect("tracking:history")
    
    entry_queryset = apply_history_limit(
        DailyEntry.objects.filter(user=request.user),
        request.user,
        today=get_user_today(request.user),
    )
    entry = get_object_or_404(entry_queryset, date=entry_date)
    
    return render(request, "tracking/entry_detail_new.html", {
        "entry": entry,
    })


@login_required
def delete_entry_view(request, date_str):
    """Delete an entry by date."""
    try:
        entry_date = date.fromisoformat(date_str)
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect("tracking:history")
    
    entry_queryset = apply_history_limit(
        DailyEntry.objects.filter(user=request.user),
        request.user,
        today=get_user_today(request.user),
    )
    entry = get_object_or_404(entry_queryset, date=entry_date)
    
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Entry deleted successfully.")
        return redirect("tracking:today")
    
    return render(request, "tracking/confirm_delete_new.html", {
        "entry": entry,
    })


@login_required
def delete_entry_by_id_view(request, entry_id):
    """Delete an entry by ID (for modal delete)."""
    entry = get_object_or_404(
        apply_history_limit(
            DailyEntry.objects.filter(user=request.user),
            request.user,
            today=get_user_today(request.user),
        ),
        id=entry_id,
    )
    
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Entry deleted successfully.")
        return redirect("tracking:today")
    
    return redirect("tracking:today")


# HTMX partial views
@login_required
def chart_data_view(request):
    """Return chart data as JSON for HTMX updates."""
    today = get_user_today(request.user)
    try:
        days = max(1, min(365, int(request.GET.get("days", 30))))
    except (ValueError, TypeError):
        days = 30
    limit_days = get_history_limit_days(request.user)
    if limit_days is not None:
        days = min(days, limit_days)
    start_date = today - timedelta(days=days - 1)
    
    entries_query = DailyEntry.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=today,
    ).order_by("date")
    entries = apply_history_limit(entries_query, request.user, today=today)
    
    # Materialize queryset into a dict for O(1) lookups (avoids re-evaluating
    # the lazy queryset on every iteration which causes repeated DB hits)
    entry_by_date = {e.date: e.score for e in entries.only("date", "score")}
    
    data = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        score = entry_by_date.get(day)
        data.append({
            "date": day.isoformat(),
            "score": score,
        })
    
    return JsonResponse({"data": data})


# Export views
@login_required
def export_page_view(request):
    """Render the export options page."""
    today = get_user_today(request.user)
    is_premium = has_entitlement(request.user, "premium_access")
    
    # For CSV, all users can access all data — no history restriction
    all_entries = DailyEntry.objects.filter(user=request.user)
    first_entry_all = all_entries.only("date").order_by("date").first()
    last_entry_all = all_entries.only("date").order_by("-date").first()
    total_entries_all = all_entries.count()
    
    return render(request, "tracking/export.html", {
        "today": today,
        "first_entry_date": first_entry_all.date if first_entry_all else today,
        "last_entry_date": last_entry_all.date if last_entry_all else today,
        "total_entries": total_entries_all,
        "has_entries": total_entries_all > 0,
        "is_premium": is_premium,
    })


@login_required
def export_csv_view(request):
    """Generate and download CSV export.
    
    CSV exports are available to ALL users with no date-range restriction.
    This ensures every user can always access all of their data.
    """
    from .exports import CSUExporter
    
    report_type = request.GET.get("report_type", "quick")
    
    # Free users can only export quick summary
    if not has_entitlement(request.user, "reports_advanced") and report_type != "quick":
        messages.error(request, "Detailed reports are a Cura Premium feature. Upgrade to access full reports.")
        return redirect("subscriptions:premium")
    
    today = get_user_today(request.user)
    
    # Parse date range from request
    try:
        start_date = date.fromisoformat(request.GET.get("start", (today - timedelta(days=29)).isoformat()))
        end_date = date.fromisoformat(request.GET.get("end", today.isoformat()))
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect("tracking:export")
    
    # CSV exports have NO date-range restriction — all users can export
    # their full history. Only clamp end_date to today.
    if end_date > today:
        end_date = today
    if start_date > end_date:
        messages.error(request, "Start date must be before end date.")
        return redirect("tracking:export")
    
    # Parse options
    options = {
        "anonymize": request.GET.get("anonymize") == "1",
        "include_notes": request.GET.get("notes", "1") == "1",
        "include_antihistamine": request.GET.get("antihistamine", "1") == "1",
        "include_breakdown": request.GET.get("breakdown", "1") == "1",
        "report_type": request.GET.get("report_type", "quick"),
    }
    
    try:
        exporter = CSUExporter(request.user, start_date, end_date, options)
        return exporter.export_csv()
    except Exception as e:
        # Log the error for debugging but don't expose details to user
        import logging
        logging.error(f"CSV export failed for user {request.user.id}: {e}")
        messages.error(request, "Export failed. Please try again or contact support if the problem persists.")
        return redirect("tracking:export")


@login_required
def export_pdf_view(request):
    """Generate and return a PDF export.
    
    PDF exports are a Premium feature. Free users are redirected to upgrade.
    
    Query parameters:
        action: 'view' returns the PDF with Content-Disposition: inline
                (default) returns as attachment for download
    """
    from .exports import CSUExporter
    
    # PDF reports are a premium feature
    if not has_entitlement(request.user, "premium_access"):
        messages.info(
            request,
            "PDF reports are a Cura Premium feature. You can always download your data as a CSV file.",
        )
        return redirect("subscriptions:premium")
    
    report_type = request.GET.get("report_type", "quick")
    
    today = get_user_today(request.user)
    
    # Parse date range from request
    try:
        start_date = date.fromisoformat(request.GET.get("start", (today - timedelta(days=29)).isoformat()))
        end_date = date.fromisoformat(request.GET.get("end", today.isoformat()))
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect("tracking:export")
    
    # Premium users have full history access
    if end_date > today:
        end_date = today
    if start_date > end_date:
        messages.error(request, "Start date must be before end date.")
        return redirect("tracking:export")
    
    # Parse options
    options = {
        "anonymize": request.GET.get("anonymize") == "1",
        "include_notes": request.GET.get("notes", "1") == "1",
        "include_antihistamine": request.GET.get("antihistamine", "1") == "1",
        "include_breakdown": request.GET.get("breakdown", "1") == "1",
        "report_type": report_type,
    }
    
    inline = request.GET.get("action") == "view"
    
    try:
        exporter = CSUExporter(request.user, start_date, end_date, options)
        return exporter.export_pdf(inline=inline)
    except Exception as e:
        # Log the error for debugging but don't expose details to user
        import logging
        logging.error(f"PDF export failed for user {request.user.id}: {e}")
        messages.error(request, "Export failed. Please try again or contact support if the problem persists.")
        return redirect("tracking:export")


@login_required
def export_pdf_preview_view(request):
    """Render an in-app page that embeds the PDF in an object element.
    
    Users can view the PDF inline and download it without leaving the app.
    """
    if not has_entitlement(request.user, "premium_access"):
        messages.info(
            request,
            "PDF reports are a Cura Premium feature. You can always download your data as a CSV file.",
        )
        return redirect("subscriptions:premium")
    
    # Build the query string for the PDF iframe src and download link.
    # Forward all GET params (dates, options, report_type) to the PDF endpoint.
    params = request.GET.copy()
    
    # Inline view URL (Content-Disposition: inline)
    view_params = params.copy()
    view_params["action"] = "view"
    
    # Download URL (Content-Disposition: attachment) — no action param
    download_params = params.copy()
    download_params.pop("action", None)
    
    report_type = params.get("report_type", "quick")
    
    return render(request, "tracking/export_pdf_preview.html", {
        "pdf_view_url": f"{reverse('tracking:export_pdf')}?{view_params.urlencode()}",
        "pdf_download_url": f"{reverse('tracking:export_pdf')}?{download_params.urlencode()}",
        "report_type": report_type,
    })


@login_required
def export_my_data_view(request):
    """Download a comprehensive CSV containing ALL data held about the user.
    
    Available to every user regardless of subscription tier.
    This fulfils data-portability / subject-access requirements.
    """
    from .exports import export_my_data_csv
    
    try:
        return export_my_data_csv(request.user)
    except Exception as e:
        import logging
        logging.error(f"My-data CSV export failed for user {request.user.id}: {e}")
        messages.error(request, "Export failed. Please try again or contact support if the problem persists.")
        return redirect("tracking:export")
