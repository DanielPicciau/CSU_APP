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

# Configure logging
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
REMINDER_WINDOW = 90  # 1.5 minutes to account for slight timing variations


def process_reminders():
    """Check and send any due reminders."""
    utc_now = timezone.now()
    sent_count = 0
    
    # Get all users with reminders enabled
    preferences = ReminderPreferences.objects.filter(
        enabled=True,
    ).select_related('user')
    
    for pref in preferences:
        user = pref.user
        
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
                    logger.error(f"Push failed for {user.email}: {e}")
            
            # Log the reminder
            ReminderLog.objects.create(
                user=user,
                date=user_today,
                success=success_count > 0,
                subscriptions_notified=success_count
            )
            
            if success_count > 0:
                sent_count += 1
                logger.info(f"✓ Sent reminder to {user.email} ({success_count} devices)")
            
        except Exception as e:
            logger.error(f"Error processing {user.email}: {e}")
    
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
            now = datetime.now()
            logger.info(f"Checking reminders at {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            sent = process_reminders()
            if sent > 0:
                logger.info(f"Sent {sent} reminder(s)")
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            # Don't crash, just log and continue
        
        # Sleep until next check
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
