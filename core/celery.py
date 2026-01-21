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
}
