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
    3. Query string (legacy, discouraged)
    
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
        # Try X-Cron-Token header
        token = request.headers.get('X-Cron-Token', '')
    
    # Fallback to query string (legacy support, log warning)
    if not token:
        token = request.GET.get('token', '')
        if token:
            import logging
            logging.getLogger('security').warning(
                'Cron token passed via query string - migrate to Authorization header'
            )
    
    if not token:
        return False
    
    # Constant-time comparison to prevent timing attacks
    return secrets.compare_digest(token, cron_secret)


@login_required
def reminder_settings_view(request):
    """View and update reminder preferences."""
    # Get or create preferences
    preferences, created = ReminderPreferences.objects.get_or_create(user=request.user)
    
    # Get active subscriptions count
    subscriptions_count = PushSubscription.objects.filter(
        user=request.user,
        is_active=True,
    ).count()
    
    if request.method == "POST":
        form = ReminderPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
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


# Window for sending reminders (in seconds) - reduced to prevent overlap
REMINDER_WINDOW = 60  # 1 minute (cron runs every minute)


@require_http_methods(["GET", "POST"])
def cron_send_reminders(request):
    """
    Webhook endpoint for external cron service to trigger reminders.
    
    Authentication: Use Authorization header with Bearer token (preferred)
    Example: Authorization: Bearer YOUR_SECRET
    
    Alternative: X-Cron-Token header or ?token= query param (legacy)
    
    Add ?force=1 to bypass all checks and send immediately (for testing).
    
    IMPORTANT: This function ensures exactly ONE reminder per user per day:
    1. Checks ReminderLog for existing reminder on this date
    2. Checks ReminderPreferences.last_reminder_date as a secondary guard
    3. Updates both after sending to prevent duplicates
    """
    # Verify the secret token using secure comparison
    if not verify_cron_token(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)
    
    force = request.GET.get('force') == '1'
    
    # Process reminders
    utc_now = timezone.now()
    sent_count = 0
    checked_count = 0
    skipped_reasons = {}  # Aggregate skip reasons for privacy
    
    preferences = ReminderPreferences.objects.filter(
        enabled=True,
    ).select_related('user')
    
    for pref in preferences:
        user = pref.user
        checked_count += 1
        
        try:
            # Get current time in user's timezone
            try:
                user_tz = pytz.timezone(pref.timezone)
            except pytz.UnknownTimeZoneError:
                user_tz = pytz.timezone('UTC')
            
            user_now = utc_now.astimezone(user_tz)
            user_today = user_now.date()
            
            # Build the reminder datetime for today
            reminder_datetime = user_tz.localize(
                datetime.combine(user_today, pref.time_of_day)
            )
            
            # Calculate time since reminder
            time_since = (user_now - reminder_datetime).total_seconds()
            
            # Skip checks if force mode
            if not force:
                # PRIMARY GUARD: Check if already reminded today via preferences field
                # This is the most reliable check since it's on the same record we're processing
                if pref.last_reminder_date == user_today:
                    skipped_reasons["already_reminded"] = skipped_reasons.get("already_reminded", 0) + 1
                    continue
                
                # Check if within the window (just passed, not too long ago)
                if time_since < 0:
                    skipped_reasons["not_time_yet"] = skipped_reasons.get("not_time_yet", 0) + 1
                    continue
                if time_since > REMINDER_WINDOW:
                    skipped_reasons["outside_window"] = skipped_reasons.get("outside_window", 0) + 1
                    continue
                
                # SECONDARY GUARD: Check ReminderLog (for redundancy)
                if ReminderLog.objects.filter(user=user, date=user_today).exists():
                    skipped_reasons["already_logged_reminder"] = skipped_reasons.get("already_logged_reminder", 0) + 1
                    # Also update pref guard to stay in sync
                    pref.last_reminder_date = user_today
                    pref.save(update_fields=['last_reminder_date'])
                    continue
                
                # Check if already logged today (no need to remind)
                if DailyEntry.objects.filter(user=user, date=user_today).exists():
                    skipped_reasons["already_logged_entry"] = skipped_reasons.get("already_logged_entry", 0) + 1
                    continue
            
            # Get active subscriptions
            subscriptions = PushSubscription.objects.filter(
                user=user,
                is_active=True
            )
            
            if not subscriptions.exists():
                skipped_reasons["no_subscriptions"] = skipped_reasons.get("no_subscriptions", 0) + 1
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
                        tag=f"reminder-{user_today.isoformat()}"
                    ):
                        success_count += 1
                except Exception as e:
                    pass
            
            # Log the reminder in ReminderLog table
            ReminderLog.objects.create(
                user=user,
                date=user_today,
                success=success_count > 0,
                subscriptions_notified=success_count
            )
            
            # Update the guard fields on ReminderPreferences to prevent re-sending
            pref.last_reminder_date = user_today
            pref.last_reminder_sent_at = utc_now
            pref.save(update_fields=['last_reminder_date', 'last_reminder_sent_at'])
            
            if success_count > 0:
                sent_count += 1
            
        except Exception as e:
            # Log error without exposing user info in response
            import logging
            logging.getLogger('notifications').error(f"Reminder error for user {user.id}: {e}")
            skipped_reasons["error"] = skipped_reasons.get("error", 0) + 1
    
    # Return anonymized summary (no user emails or PII)
    return JsonResponse({
        "status": "ok",
        "timestamp": utc_now.isoformat(),
        "checked": checked_count,
        "sent": sent_count,
        "skipped": skipped_reasons,
    })
