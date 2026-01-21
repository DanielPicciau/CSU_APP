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

print("=" * 50, flush=True)
print("CSU Tracker Reminder Daemon", flush=True)
print("Initializing Django...", flush=True)

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

print("Django initialized successfully", flush=True)

import pytz
from django.utils import timezone

from notifications.models import ReminderPreferences, ReminderLog, PushSubscription
from notifications.push import send_push_notification
from tracking.models import DailyEntry

print("All imports complete", flush=True)

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
    
    print(f"  Found {preferences.count()} user(s) with reminders enabled", flush=True)
    
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
            
            print(f"  User: {user.email}", flush=True)
            print(f"    Reminder time: {pref.time_of_day} ({pref.timezone})", flush=True)
            print(f"    Current time:  {user_now.strftime('%H:%M:%S')}", flush=True)
            print(f"    Time since:    {int(time_since)}s", flush=True)
            
            # Check if within the window (just passed, not too long ago)
            if time_since < 0:
                print(f"    SKIP: Reminder time not yet reached", flush=True)
                continue
            if time_since > REMINDER_WINDOW:
                print(f"    SKIP: Outside window (>{REMINDER_WINDOW}s ago)", flush=True)
                continue
            
            # Check if already reminded today
            if ReminderLog.objects.filter(user=user, date=user_today).exists():
                print(f"    SKIP: Already reminded today", flush=True)
                continue
            
            # Check if already logged today
            if DailyEntry.objects.filter(user=user, date=user_today).exists():
                print(f"    SKIP: Already logged today", flush=True)
                continue
            
            # Get active subscriptions
            subscriptions = PushSubscription.objects.filter(
                user=user,
                is_active=True
            )
            
            if not subscriptions.exists():
                print(f"    SKIP: No active push subscriptions", flush=True)
                continue
            
            print(f"    SENDING to {subscriptions.count()} device(s)...", flush=True)
            
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
                    print(f"    Push result: {result}", flush=True)
                    if result:
                        success_count += 1
                except Exception as e:
                    print(f"    Push ERROR: {e}", flush=True)
            
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
    print("=" * 50, flush=True)
    print("CSU Tracker Reminder Daemon Started", flush=True)
    print(f"Checking every {CHECK_INTERVAL} seconds", flush=True)
    print(f"Reminder window: {REMINDER_WINDOW} seconds", flush=True)
    print("=" * 50, flush=True)
    
    while True:
        try:
            now = datetime.now()
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Checking reminders...", flush=True)
            
            sent = process_reminders()
            if sent > 0:
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Sent {sent} reminder(s)", flush=True)
            
        except Exception as e:
            print(f"Error in main loop: {e}", flush=True)
            # Don't crash, just log and continue
        
        # Sleep until next check
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
