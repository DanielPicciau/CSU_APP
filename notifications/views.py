"""
Views for the notifications app (Django templates).
"""

import hashlib
import hmac
import secrets
from datetime import datetime

import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import ReminderPreferencesForm
from .models import ReminderPreferences, PushSubscription, ReminderLog
from .push import send_push_notification
from tracking.models import DailyEntry


def verify_cron_token(request) -> bool:
    """
    Securely verify the cron webhook token.
    
    Accepts token via:
    1. Authorization header (preferred): "Bearer <token>"
    2. X-Cron-Token header (alternative)
    
    Uses constant-time comparison to prevent timing attacks.
    """
    cron_secret = getattr(settings, 'CRON_WEBHOOK_SECRET', None)
    if not cron_secret:
        return False
    
    # Try Authorization header first (preferred)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        # Try X-Cron-Token header (alternative)
        token = request.headers.get('X-Cron-Token', '')
    
    if not token:
        return False
    
    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(token, cron_secret)


@login_required
def reminder_settings_view(request):
    """View and update reminder preferences."""
    # Avoid DB writes on GET; create only when saving.
    preferences = ReminderPreferences.objects.filter(user=request.user).first()
    if not preferences:
        preferences = ReminderPreferences(user=request.user)
    
    # Get active subscriptions count
    subscriptions_count = PushSubscription.objects.filter(
        user=request.user,
        is_active=True,
    ).count()
    
    if request.method == "POST":
        form = ReminderPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            pref = form.save(commit=False)
            if not pref.user_id:
                pref.user = request.user
            pref.save()
            messages.success(request, "Reminder settings updated!")
            return redirect("notifications:settings")
    else:
        form = ReminderPreferencesForm(instance=preferences)
    
    return render(request, "notifications/settings_new.html", {
        "form": form,
        "preferences": preferences,
        "subscriptions_count": subscriptions_count,
    })


@login_required
def subscriptions_list_view(request):
    """List user's push subscriptions."""
    subscriptions = PushSubscription.objects.filter(
        user=request.user,
    ).order_by("-created_at")
    
    return render(request, "notifications/subscriptions.html", {
        "subscriptions": subscriptions,
    })


@login_required
def delete_subscription_view(request, subscription_id):
    """Delete a push subscription."""
    if request.method == "POST":
        try:
            subscription = PushSubscription.objects.get(
                pk=subscription_id,
                user=request.user,
            )
            subscription.delete()
            messages.success(request, "Subscription removed.")
        except PushSubscription.DoesNotExist:
            messages.error(request, "Subscription not found.")
    
    return redirect("notifications:subscriptions")


@login_required
def test_notification_view(request):
    """Send a test notification."""
    from .tasks import send_test_notification
    
    if request.method == "POST":
        # Send test notification async
        send_test_notification.delay(request.user.id)
        return JsonResponse({"status": "sent"})
    
    return JsonResponse({"error": "POST required"}, status=405)


# Window for sending reminders (in seconds)
# This allows flexibility for cron timing - if cron runs late, we still send
# We prevent duplicates via ReminderLog and last_reminder_date guards
REMINDER_WINDOW = 3600  # 1 hour window to catch the reminder

# UK timezone for all time calculations
UK_TZ = pytz.timezone("Europe/London")


def get_uk_now():
    """Get current datetime in UK timezone."""
    return timezone.now().astimezone(UK_TZ)


@require_http_methods(["GET", "POST"])
def cron_send_reminders(request):
    """
    Webhook endpoint for external cron service to trigger reminders.
    
    Authentication: Use Authorization header with Bearer token (preferred)
    Example: Authorization: Bearer YOUR_SECRET
    
    Add ?force=1 to bypass all checks and send immediately (for testing).
    Add ?debug=1 to see detailed info about each user.
    
    SIMPLIFIED LOGIC (all times in UK timezone):
    1. Get current UK time
    2. For each user with reminders enabled:
       - If current UK time >= their reminder time (today)
       - AND we haven't reminded them today
       - AND they haven't logged an entry today
       - Then send the reminder
    """
    # Verify the secret token using secure comparison
    if not verify_cron_token(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    
    force = request.GET.get('force') == '1'
    debug = request.GET.get('debug') == '1'
    
    # Get current UK time (this is the ONLY timezone we use)
    uk_now = get_uk_now()
    uk_today = uk_now.date()
    current_hour = uk_now.hour
    current_minute = uk_now.minute
    
    sent_count = 0
    checked_count = 0
    skipped_reasons = {}
    debug_info = [] if debug else None
    
    preferences = ReminderPreferences.objects.filter(
        enabled=True,
    ).select_related('user')
    
    for pref in preferences:
        user = pref.user
        checked_count += 1
        
        try:
            # Get the reminder time (hour and minute)
            reminder_hour = pref.time_of_day.hour
            reminder_minute = pref.time_of_day.minute
            
            if debug:
                debug_info.append({
                    "user_id": user.id,
                    "reminder_time": f"{reminder_hour:02d}:{reminder_minute:02d}",
                    "current_uk_time": f"{current_hour:02d}:{current_minute:02d}",
                    "last_reminder_date": str(pref.last_reminder_date),
                    "uk_today": str(uk_today),
                })
            
            if not force:
                # Check if already reminded today
                if pref.last_reminder_date == uk_today:
                    skipped_reasons["already_reminded"] = skipped_reasons.get("already_reminded", 0) + 1
                    if debug:
                        debug_info[-1]["status"] = "already_reminded"
                    continue
                
                # Check if it's past the reminder time (simple comparison)
                current_minutes = current_hour * 60 + current_minute
                reminder_minutes = reminder_hour * 60 + reminder_minute
                
                if current_minutes < reminder_minutes:
                    skipped_reasons["not_time_yet"] = skipped_reasons.get("not_time_yet", 0) + 1
                    if debug:
                        debug_info[-1]["status"] = "not_time_yet"
                    continue
                
                # Check if already logged today
                if DailyEntry.objects.filter(user=user, date=uk_today).exists():
                    skipped_reasons["already_logged_entry"] = skipped_reasons.get("already_logged_entry", 0) + 1
                    if debug:
                        debug_info[-1]["status"] = "already_logged"
                    continue
            
            # Get active subscriptions
            subscriptions = PushSubscription.objects.filter(
                user=user,
                is_active=True
            )
            
            if not subscriptions.exists():
                skipped_reasons["no_subscriptions"] = skipped_reasons.get("no_subscriptions", 0) + 1
                if debug:
                    debug_info[-1]["status"] = "no_subscriptions"
                continue
            
            # Send notifications
            success_count = 0
            for subscription in subscriptions:
                try:
                    if send_push_notification(
                        subscription=subscription,
                        title="CSU Tracker Reminder",
                        body="Time to log your CSU score for today!",
                        url="/tracking/today/",
                        tag=f"reminder-{uk_today.isoformat()}"
                    ):
                        success_count += 1
                except Exception as e:
                    pass
            
            # Log the reminder in ReminderLog table
            ReminderLog.objects.update_or_create(
                user=user,
                date=uk_today,
                defaults={
                    "success": success_count > 0,
                    "subscriptions_notified": success_count,
                }
            )
            
            # Update the guard field on ReminderPreferences to prevent re-sending
            pref.last_reminder_date = uk_today
            pref.save(update_fields=['last_reminder_date'])
            
            if success_count > 0:
                sent_count += 1
                if debug:
                    debug_info[-1]["status"] = f"sent_{success_count}"
            
        except Exception as e:
            # Log error without exposing user info in response
            import logging
            logging.getLogger('notifications').error(f"Reminder error for user {user.id}: {e}")
            skipped_reasons["error"] = skipped_reasons.get("error", 0) + 1
            if debug:
                debug_info[-1]["status"] = f"error: {str(e)}"
    
    # Build response
    response_data = {
        "status": "ok",
        "uk_time": uk_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "uk_date": str(uk_today),
        "checked": checked_count,
        "sent": sent_count,
        "skipped": skipped_reasons,
    }
    
    if debug:
        response_data["debug"] = debug_info
    
    return JsonResponse(response_data)
