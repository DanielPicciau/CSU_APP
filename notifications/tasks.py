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
    preferences = list(ReminderPreferences.objects.filter(
        enabled=True,
        user__push_subscriptions__is_active=True,
    ).select_related("user").distinct())

    # Prefetch per-user data in bulk to avoid N+1 queries.
    # Because users may span multiple timezones we collect dates first then
    # do bulk lookups.  We use today in UTC ± 1 day which covers every
    # IANA timezone offset (max UTC+14 / UTC-12).
    pref_user_ids = [p.user_id for p in preferences]
    utc_today = timezone.now().date()
    date_range = [utc_today - timedelta(days=1), utc_today, utc_today + timedelta(days=1)]

    entries_user_date = set(
        DailyEntry.objects.filter(
            user_id__in=pref_user_ids,
            date__in=date_range,
        ).values_list("user_id", "date")
    )

    reminded_user_date = set(
        ReminderLog.objects.filter(
            user_id__in=pref_user_ids,
            date__in=date_range,
        ).values_list("user_id", "date")
    )

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
            
            # Check if entry exists for today (prefetched)
            if (user.id, user_today) in entries_user_date:
                continue
            
            # Check if reminder already sent today (prefetched)
            if (user.id, user_today) in reminded_user_date:
                continue
            
            # Send reminder
            success_count = send_push_to_user(
                user=user,
                title="CSU Tracker Reminder",
                body="Don't forget to log your CSU score for today!",
                url="/tracking/log/",
                tag=f"reminder-{user_today.isoformat()}",
            )
            
            # Log the reminder (update_or_create to handle race conditions)
            ReminderLog.objects.update_or_create(
                user=user,
                date=user_today,
                defaults={
                    "success": success_count > 0,
                    "subscriptions_notified": success_count,
                },
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


@shared_task(name="notifications.tasks.reset_daily_reminder_flags")
def reset_daily_reminder_flags():
    """
    Reset all reminder guard fields at midnight so that notifications
    can be sent again the next day.

    This runs once daily (e.g. 00:05) as a safety net. The per-user
    day-rollover logic inside the send tasks also resets these fields,
    but this task guarantees a clean slate even if those paths don't run.
    """
    count = ReminderPreferences.objects.filter(
        last_reminder_date__isnull=False,
    ).update(
        last_reminder_date=None,
        last_reminder_sent_at=None,
    )
    logger.info(f"Reset reminder flags for {count} users.")
    return count


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
