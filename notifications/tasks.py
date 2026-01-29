"""
Celery tasks for notifications.
"""

import logging
from datetime import date, datetime, timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

import pytz

from .models import ReminderPreferences, ReminderLog
from .push import send_push_to_user
from core.security import hash_sensitive_data

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(name="notifications.tasks.process_daily_reminders")
def process_daily_reminders():
    """
    Process and send daily reminder notifications.
    
    This task runs every 5 minutes and checks which users:
    1. Have reminders enabled
    2. It is past their reminder time in their timezone
    3. Have NOT submitted today's entry
    4. Have NOT already been reminded today
    
    Then sends push notifications to their subscriptions.
    """
    from tracking.models import DailyEntry
    
    logger.info("Starting daily reminder processing")
    
    # Get all users with reminders enabled
    preferences = ReminderPreferences.objects.filter(
        enabled=True,
        user__push_subscriptions__is_active=True,
    ).select_related("user").distinct()
    
    reminders_sent = 0
    
    for pref in preferences:
        user = pref.user
        
        try:
            # Get current time in user's timezone
            user_tz = pytz.timezone(pref.timezone)
            user_now = timezone.now().astimezone(user_tz)
            user_today = user_now.date()

            # Reset "sent" status when the day rolls over in the user's timezone.
            if pref.last_reminder_date and pref.last_reminder_date < user_today:
                pref.last_reminder_date = None
                pref.last_reminder_sent_at = None
                pref.save(update_fields=["last_reminder_date", "last_reminder_sent_at"])
            
            # Create reminder datetime for today
            reminder_time = datetime.combine(
                user_today,
                pref.time_of_day,
                tzinfo=user_tz,
            )
            
            # Check if it's past reminder time
            if user_now < reminder_time:
                continue
            
            # Check if entry exists for today
            if DailyEntry.objects.filter(user=user, date=user_today).exists():
                continue
            
            # Check if reminder already sent today
            if ReminderLog.objects.filter(user=user, date=user_today).exists():
                continue
            
            # Send reminder
            success_count = send_push_to_user(
                user=user,
                title="CSU Tracker Reminder",
                body="Don't forget to log your CSU score for today!",
                url="/tracking/log/",
                tag=f"reminder-{user_today.isoformat()}",
            )
            
            # Log the reminder
            ReminderLog.objects.create(
                user=user,
                date=user_today,
                success=success_count > 0,
                subscriptions_notified=success_count,
            )

            # Store guard fields for UI/status consistency
            pref.last_reminder_date = user_today
            pref.last_reminder_sent_at = timezone.now()
            pref.save(update_fields=["last_reminder_date", "last_reminder_sent_at"])
            
            if success_count > 0:
                reminders_sent += 1
                logger.info(
                    "Reminder sent to user_id=%s user_hash=%s (%s subscriptions)",
                    user.id,
                    hash_sensitive_data(user.email),
                    success_count,
                )
            else:
                logger.warning(
                    "Failed to send reminder to user_id=%s user_hash=%s",
                    user.id,
                    hash_sensitive_data(user.email),
                )
                
        except Exception as e:
            logger.error(
                "Error processing reminder for user_id=%s user_hash=%s: %s",
                user.id,
                hash_sensitive_data(user.email),
                e,
            )
            continue
    
    logger.info(f"Daily reminder processing complete. Sent {reminders_sent} reminders.")
    return reminders_sent


@shared_task(name="notifications.tasks.send_test_notification")
def send_test_notification(user_id: int):
    """Send a test notification to a user."""
    try:
        user = User.objects.get(pk=user_id)
        count = send_push_to_user(
            user=user,
            title="Test Notification",
            body="Your push notifications are working!",
            url="/",
            tag="test",
        )
        return f"Sent to {count} subscriptions"
    except User.DoesNotExist:
        return "User not found"
