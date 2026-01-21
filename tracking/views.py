"""
Views for the tracking app (Django templates).
"""

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse

import pytz

from .models import DailyEntry
from .forms import DailyEntryForm


def get_user_today(user) -> date:
    """Get today's date in the user's timezone."""
    user_tz = pytz.timezone(user.profile.default_timezone)
    return timezone.now().astimezone(user_tz).date()


@login_required
def home_view(request):
    """Home page - shows today's status and quick actions."""
    today = get_user_today(request.user)
    today_entry = DailyEntry.objects.filter(user=request.user, date=today).first()
    
    # Get last 7 days of entries for the mini chart
    week_ago = today - timedelta(days=6)
    recent_entries = DailyEntry.objects.filter(
        user=request.user,
        date__gte=week_ago,
        date__lte=today,
    ).order_by("date")
    
    # Build chart data (fill in missing days with None)
    chart_data = []
    for i in range(7):
        day = week_ago + timedelta(days=i)
        entry = next((e for e in recent_entries if e.date == day), None)
        chart_data.append({
            "date": day,
            "score": entry.score if entry else None,
            "has_entry": entry is not None,
        })
    
    # Calculate UAS7 (last 7 days sum)
    uas7_entries = list(recent_entries)
    uas7_score = sum(e.score for e in uas7_entries)
    uas7_complete = len(uas7_entries) == 7
    
    # Streak calculation
    streak = 0
    check_date = today
    while True:
        if DailyEntry.objects.filter(user=request.user, date=check_date).exists():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    return render(request, "tracking/home.html", {
        "today": today,
        "today_entry": today_entry,
        "chart_data": chart_data,
        "uas7_score": uas7_score,
        "uas7_complete": uas7_complete,
        "streak": streak,
    })


@login_required
def log_entry_view(request, date_str=None):
    """Log or update a daily entry."""
    if date_str:
        try:
            entry_date = date.fromisoformat(date_str)
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("home")
    else:
        entry_date = get_user_today(request.user)
    
    # Check if entry exists (for update)
    existing_entry = DailyEntry.objects.filter(
        user=request.user,
        date=entry_date,
    ).first()
    
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
            return redirect("home")
    else:
        form = DailyEntryForm(
            instance=existing_entry,
            user=request.user,
            entry_date=entry_date,
        )
    
    return render(request, "tracking/log_entry.html", {
        "form": form,
        "entry_date": entry_date,
        "is_today": entry_date == get_user_today(request.user),
        "existing_entry": existing_entry,
    })


@login_required
def history_view(request):
    """View entry history."""
    today = get_user_today(request.user)
    
    # Get filter parameters
    days = int(request.GET.get("days", 30))
    start_date = today - timedelta(days=days - 1)
    
    entries = DailyEntry.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=today,
    ).order_by("-date")
    
    # Calculate statistics
    stats = entries.aggregate(
        avg_score=Avg("score"),
        total_entries=Sum("score"),
    )
    
    # Build calendar data
    calendar_data = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        entry = next((e for e in entries if e.date == day), None)
        calendar_data.append({
            "date": day,
            "entry": entry,
            "weekday": day.strftime("%a"),
        })
    
    return render(request, "tracking/history.html", {
        "entries": entries,
        "calendar_data": list(reversed(calendar_data)),
        "stats": stats,
        "days": days,
        "start_date": start_date,
        "today": today,
    })


@login_required
def entry_detail_view(request, date_str):
    """View a specific entry's details."""
    try:
        entry_date = date.fromisoformat(date_str)
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect("tracking:history")
    
    entry = get_object_or_404(
        DailyEntry,
        user=request.user,
        date=entry_date,
    )
    
    return render(request, "tracking/entry_detail.html", {
        "entry": entry,
    })


@login_required
def delete_entry_view(request, date_str):
    """Delete an entry."""
    try:
        entry_date = date.fromisoformat(date_str)
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect("tracking:history")
    
    entry = get_object_or_404(
        DailyEntry,
        user=request.user,
        date=entry_date,
    )
    
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Entry deleted successfully.")
        return redirect("tracking:history")
    
    return render(request, "tracking/confirm_delete.html", {
        "entry": entry,
    })


# HTMX partial views
@login_required
def chart_data_view(request):
    """Return chart data as JSON for HTMX updates."""
    today = get_user_today(request.user)
    days = int(request.GET.get("days", 30))
    start_date = today - timedelta(days=days - 1)
    
    entries = DailyEntry.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=today,
    ).order_by("date")
    
    data = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        entry = next((e for e in entries if e.date == day), None)
        data.append({
            "date": day.isoformat(),
            "score": entry.score if entry else None,
        })
    
    return JsonResponse({"data": data})
