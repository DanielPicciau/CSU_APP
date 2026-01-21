"""
API URL routes for tracking app.
"""

from django.urls import path

from . import api_views

app_name = "tracking_api"

urlpatterns = [
    path("entries/", api_views.DailyEntryListCreateView.as_view(), name="entries"),
    path("entries/<str:date>/", api_views.DailyEntryDetailView.as_view(), name="entry_detail"),
    path("today/", api_views.TodayEntryView.as_view(), name="today"),
    path("adherence/", api_views.AdherenceMetricsView.as_view(), name="adherence"),
    path("weekly/", api_views.WeeklyStatsView.as_view(), name="weekly"),
]
