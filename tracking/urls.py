"""
URL routes for tracking app (template views).
"""

from django.urls import path

from . import views

app_name = "tracking"

urlpatterns = [
    path("", views.today_view, name="today"),
    path("log/", views.log_entry_view, name="log_entry"),
    path("log/<str:date_str>/", views.log_entry_view, name="log_entry_date"),
    path("history/", views.history_view, name="history"),
    path("insights/", views.insights_view, name="insights"),
    path("export/", views.export_page_view, name="export"),
    path("export/csv/", views.export_csv_view, name="export_csv"),
    path("export/pdf/", views.export_pdf_view, name="export_pdf"),
    path("export/pdf/preview/", views.export_pdf_preview_view, name="export_pdf_preview"),
    path("export/my-data/", views.export_my_data_view, name="export_my_data"),
    path("entry/<str:date_str>/", views.entry_detail_view, name="entry_detail"),
    path("entry/<str:date_str>/delete/", views.delete_entry_view, name="delete_entry"),
    path("entry/delete/<int:entry_id>/", views.delete_entry_by_id_view, name="delete_entry_by_id"),
    path("api/chart-data/", views.chart_data_view, name="chart_data"),
]
