"""
API URL routes for notifications app.
"""

from django.urls import path

from . import api_views

app_name = "notifications_api"

urlpatterns = [
    path("subscribe/", api_views.PushSubscriptionCreateView.as_view(), name="subscribe"),
    path("unsubscribe/", api_views.PushSubscriptionDeleteView.as_view(), name="unsubscribe"),
    path("preferences/", api_views.ReminderPreferencesView.as_view(), name="preferences"),
    path("test/", api_views.TestNotificationView.as_view(), name="test"),
]
