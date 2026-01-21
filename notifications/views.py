"""
Views for the notifications app (Django templates).
"""

import hashlib
import hmac
from datetime import datetime

import pytz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import ReminderPreferencesForm
from .models import ReminderPreferences, PushSubscription, ReminderLog
from .push import send_push_notification
from tracking.models import DailyEntry


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


# Webhook secret for cron service authentication
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
CRON_WEBHOOK_SECRET = getattr(settings, 'CRON_WEBHOOK_SECRET', None)

# Window for sending reminders (in seconds)
REMINDER_WINDOW = 90  # 1.5 minutes


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cron_send_reminders(request):
    """
    Webhook endpoint for external cron service to trigger reminders.
    
    Call this every minute from cron-job.org or similar.
    URL: https://yoursite.pythonanywhere.com/notifications/cron/send-reminders/?token=YOUR_SECRET
    """
    # Verify the secret token
    token = request.GET.get('token') or request.headers.get('X-Cron-Token')
    
    if not CRON_WEBHOOK_SECRET:
        return JsonResponse({
            "error": "CRON_WEBHOOK_SECRET not configured in settings"
        }, status=500)
    
    if not token or token != CRON_WEBHOOK_SECRET:
        return JsonResponse({"error": "Invalid token"}, status=403)
    
    # Process reminders
    utc_now = timezone.now()
    sent_count = 0
    checked_count = 0
    
    preferences = ReminderPreferences.objects.filter(
        enabled=True,
    ).select_related('user')
    
    results = []
    
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
            
            # Check if within the window (just passed, not too long ago)
            if time_since < 0 or time_since > REMINDER_WINDOW:
                continue
            
            # Check if already reminded today
            if ReminderLog.objects.filter(user=user, date=user_today).exists():
                continue
            
            # Check if already logged today
            if DailyEntry.objects.filter(user=user, date=user_today).exists():
                continue
            
            # Get active subscriptions
            subscriptions = PushSubscription.objects.filter(
                user=user,
                is_active=True
            )
            
            if not subscriptions.exists():
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
            
            # Log the reminder
            ReminderLog.objects.create(
                user=user,
                date=user_today,
                success=success_count > 0,
                subscriptions_notified=success_count
            )
            
            if success_count > 0:
                sent_count += 1
                results.append(f"Sent to {user.email}")
            
        except Exception as e:
            results.append(f"Error for {user.email}: {str(e)}")
    
    return JsonResponse({
        "status": "ok",
        "timestamp": utc_now.isoformat(),
        "checked": checked_count,
        "sent": sent_count,
        "details": results
    })
