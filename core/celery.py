"""
Celery configuration for CSU Tracker.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("csu_tracker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    # Check for reminders to send every 5 minutes
    "send-daily-reminders": {
        "task": "notifications.tasks.process_daily_reminders",
        "schedule": crontab(minute="*/5"),
    },
    # Nightly backups for premium users
    "enqueue-nightly-backups": {
        "task": "backups.tasks.enqueue_nightly_backups",
        "schedule": crontab(minute=0, hour=2),
    },
    # Scheduled report exports
    "enqueue-scheduled-reports": {
        "task": "reporting.tasks.enqueue_scheduled_reports",
        "schedule": crontab(minute=15, hour="*/6"),
    },
    # Data retention policy enforcement (GDPR)
    "purge-inactive-accounts": {
        "task": "accounts.tasks.purge_inactive_accounts",
        "schedule": crontab(minute=0, hour=4),  # Run at 4 AM daily
    },
}
