#!/usr/bin/env python
"""
Always-on reminder daemon for PythonAnywhere.

This script runs continuously and checks every minute for reminders to send.
Add this as an Always-on task in PythonAnywhere:
    python3.10 /home/WebFlareUK/CSU_APP/scripts/reminder_daemon.py

It will send push notifications at the exact time users have configured.
"""

import os
import sys
import time
import logging
from datetime import datetime

# Force unbuffered output for PythonAnywhere
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

import pytz
from django.utils import timezone

from notifications.models import ReminderPreferences, ReminderLog, PushSubscription
from notifications.push import send_push_notification
from tracking.models import DailyEntry

# Configure logging - use logger instead of print statements
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# How often to check (in seconds)
CHECK_INTERVAL = 60  # Every minute

# Window for sending reminders (in seconds)
# If reminder time was within this many seconds ago, send it
# Duplicate prevention is handled by ReminderLog, so a larger window is safe
REMINDER_WINDOW = 300  # 5 minutes to account for timing variations


def process_reminders():
    """Check and send any due reminders."""
    utc_now = timezone.now()
    sent_count = 0
    
    # Get all users with reminders enabled
    preferences = ReminderPreferences.objects.filter(
        enabled=True,
    ).select_related('user')
    
    logger.debug(f"Found {preferences.count()} user(s) with reminders enabled")
    
    for pref in preferences:
        user = pref.user
        # Use anonymized user ID for logging (never log email in production)
        user_id = f"user_{user.id}"
        
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
            if time_since < 0:
                logger.debug(f"{user_id}: Reminder time not yet reached")
                continue
            if time_since > REMINDER_WINDOW:
                logger.debug(f"{user_id}: Outside window (>{REMINDER_WINDOW}s ago)")
                continue
            
            # Check if already reminded today
            if ReminderLog.objects.filter(user=user, date=user_today).exists():
                logger.debug(f"{user_id}: Already reminded today")
                continue
            
            # Check if already logged today
            if DailyEntry.objects.filter(user=user, date=user_today).exists():
                logger.debug(f"{user_id}: Already logged today")
                continue
            
            # Get active subscriptions
            subscriptions = PushSubscription.objects.filter(
                user=user,
                is_active=True
            )
            
            if not subscriptions.exists():
                logger.debug(f"{user_id}: No active push subscriptions")
                continue
            
            logger.info(f"{user_id}: Sending to {subscriptions.count()} device(s)")
            
            # Send notifications
            success_count = 0
            for subscription in subscriptions:
                try:
                    result = send_push_notification(
                        subscription=subscription,
                        title="CSU Tracker Reminder",
                        body="Time to log your CSU score for today!",
                        url="/tracking/today/",
                        tag=f"reminder-{user_today.isoformat()}"
                    )
                    if result:
                        success_count += 1
                except Exception as e:
                    logger.error(f"{user_id}: Push error: {type(e).__name__}")
            
            # Log the reminder
            ReminderLog.objects.create(
                user=user,
                date=user_today,
                success=success_count > 0,
                subscriptions_notified=success_count
            )
            
            if success_count > 0:
                sent_count += 1
                logger.info(f"{user_id}: Sent reminder ({success_count} devices)")
            
        except Exception as e:
            logger.error(f"{user_id}: Error processing: {type(e).__name__}")
    
    return sent_count


def main():
    """Main loop - runs forever, checking every minute."""
    logger.info("=" * 50)
    logger.info("CSU Tracker Reminder Daemon Started")
    logger.info(f"Checking every {CHECK_INTERVAL} seconds")
    logger.info(f"Reminder window: {REMINDER_WINDOW} seconds")
    logger.info("=" * 50)
    
    while True:
        try:
            logger.debug("Checking reminders...")
            
            sent = process_reminders()
            if sent > 0:
                logger.info(f"Sent {sent} reminder(s)")
            
        except Exception as e:
            logger.error(f"Error in main loop: {type(e).__name__}: {e}")
            # Don't crash, just log and continue
        
        # Sleep until next check
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
