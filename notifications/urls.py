"""
URL routes for notifications app (template views).
"""

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("settings/", views.reminder_settings_view, name="settings"),
    path("subscriptions/", views.subscriptions_list_view, name="subscriptions"),
    path("subscriptions/<int:subscription_id>/delete/", views.delete_subscription_view, name="delete_subscription"),
    path("test/", views.test_notification_view, name="test"),
    # Webhook for external cron service
    path("cron/send-reminders/", views.cron_send_reminders, name="cron_send_reminders"),
]
