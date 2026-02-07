"""
Management command to send scheduled reminder notifications.

Run this via PythonAnywhere Scheduled Tasks every hour.
This command properly handles user timezones and prevents duplicate sends.
"""

from datetime import datetime, time

import pytz
from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import ReminderPreferences, ReminderLog, PushSubscription
from notifications.push import send_push_notification
from tracking.models import DailyEntry


class Command(BaseCommand):
    help = 'Send reminder notifications to users who have not logged today'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ignore already-sent reminders (for testing)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        
        utc_now = timezone.now()
        self.stdout.write(f"Running reminder check at {utc_now.isoformat()}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no notifications will be sent"))
        
        # Get all users with reminders enabled who have active push subscriptions
        reminders = ReminderPreferences.objects.filter(
            enabled=True,
        ).select_related('user').prefetch_related('user__push_subscriptions')
        
        sent_count = 0
        skip_count = 0
        error_count = 0
        
        for pref in reminders:
            user = pref.user
            user_email = user.email
            
            try:
                # Get current time in user's timezone
                try:
                    user_tz = pytz.timezone(pref.timezone)
                except pytz.UnknownTimeZoneError:
                    user_tz = pytz.timezone('UTC')
                    self.stdout.write(
                        self.style.WARNING(f"  Unknown timezone '{pref.timezone}' for {user_email}, using UTC")
                    )
                
                user_now = utc_now.astimezone(user_tz)
                user_today = user_now.date()
                
                # Build the reminder datetime for today in user's timezone
                reminder_datetime = user_tz.localize(
                    datetime.combine(user_today, pref.time_of_day)
                )
                
                # Check if reminder time has passed today
                if user_now < reminder_datetime:
                    # Reminder time hasn't passed yet today
                    continue
                
                time_since_reminder = user_now - reminder_datetime
                self.stdout.write(
                    f"  Checking {user_email} (tz={pref.timezone}, local={user_now.strftime('%H:%M')}, "
                    f"reminder={pref.time_of_day.strftime('%H:%M')}, passed {int(time_since_reminder.total_seconds() // 60)}m ago)"
                )
                
                # Check if already reminded today (unless --force)
                if not force and ReminderLog.objects.filter(user=user, date=user_today).exists():
                    self.stdout.write(f"    Already reminded today, skipping")
                    skip_count += 1
                    continue
                
                # Check if user already logged today
                if DailyEntry.objects.filter(user=user, date=user_today).exists():
                    self.stdout.write(f"    Already logged today, skipping")
                    skip_count += 1
                    continue
                
                # Get user's active push subscriptions
                subscriptions = PushSubscription.objects.filter(
                    user=user,
                    is_active=True
                )
                
                if not subscriptions.exists():
                    self.stdout.write(f"    No active subscriptions, skipping")
                    skip_count += 1
                    continue
                
                if dry_run:
                    self.stdout.write(f"    Would send to {subscriptions.count()} device(s)")
                    sent_count += 1
                    continue
                
                # Send notification to all user's devices
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
                        self.stdout.write(
                            self.style.ERROR(f"    Push failed: {e}")
                        )
                
                # Log the reminder to prevent duplicates
                ReminderLog.objects.update_or_create(
                    user=user,
                    date=user_today,
                    defaults={
                        "success": success_count > 0,
                        "subscriptions_notified": success_count,
                    },
                )

                # Update guard fields on ReminderPreferences
                pref.last_reminder_date = user_today
                pref.last_reminder_sent_at = timezone.now()
                pref.save(update_fields=["last_reminder_date", "last_reminder_sent_at"])
                
                if success_count > 0:
                    sent_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"    Sent to {success_count} device(s)")
                    )
                else:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"    Failed to send to any device")
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  Error processing {user_email}: {e}")
                )
                continue
        
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Done! Sent: {sent_count}, Skipped: {skip_count}, Errors: {error_count}")
        )
