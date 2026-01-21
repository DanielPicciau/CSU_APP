"""
Management command to send scheduled reminder notifications.
Run this via PythonAnywhere Scheduled Tasks every hour.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from notifications.models import ReminderPreferences, PushSubscription
from notifications.push import send_push_notification
from tracking.models import Entry


class Command(BaseCommand):
    help = 'Send reminder notifications to users who have not logged today'

    def handle(self, *args, **options):
        now = timezone.now()
        current_hour = now.hour
        current_minute = now.minute
        today = now.date()
        
        self.stdout.write(f"Running reminder check at {now}")
        
        # Find users with reminders enabled for this hour
        # Allow 30 min window (e.g., if task runs at :00 or :30)
        reminders = ReminderPreferences.objects.filter(
            enabled=True,
            time_of_day__hour=current_hour,
        )
        
        sent_count = 0
        skip_count = 0
        
        for reminder in reminders:
            user = reminder.user
            
            # Check if user already logged today
            has_logged_today = Entry.objects.filter(
                user=user,
                date=today
            ).exists()
            
            if has_logged_today:
                self.stdout.write(f"  Skipping {user.username} - already logged today")
                skip_count += 1
                continue
            
            # Get user's active push subscriptions
            subscriptions = PushSubscription.objects.filter(
                user=user,
                is_active=True
            )
            
            if not subscriptions.exists():
                self.stdout.write(f"  Skipping {user.username} - no active subscriptions")
                skip_count += 1
                continue
            
            # Send notification to all user's devices
            for subscription in subscriptions:
                try:
                    send_push_notification(
                        subscription=subscription,
                        title="CSU Tracker Reminder",
                        body="Don't forget to log your CSU score today!",
                        url="/"
                    )
                    sent_count += 1
                    self.stdout.write(f"  Sent reminder to {user.username}")
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  Failed to send to {user.username}: {e}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f"Done! Sent: {sent_count}, Skipped: {skip_count}")
        )
