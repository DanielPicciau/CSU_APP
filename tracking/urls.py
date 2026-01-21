"""
URL routes for tracking app (template views).
"""

from django.urls import path

from . import views

app_name = "tracking"

urlpatterns = [
    path("log/", views.log_entry_view, name="log_entry"),
    path("log/<str:date_str>/", views.log_entry_view, name="log_entry_date"),
    path("history/", views.history_view, name="history"),
    path("entry/<str:date_str>/", views.entry_detail_view, name="entry_detail"),
    path("entry/<str:date_str>/delete/", views.delete_entry_view, name="delete_entry"),
    path("api/chart-data/", views.chart_data_view, name="chart_data"),
]
