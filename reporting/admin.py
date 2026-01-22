"""
Admin configuration for reporting models.
"""

from django.contrib import admin

from .models import ExportJob, ReportSchedule


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "format", "status", "from_date", "to_date", "created_at"]
    list_filter = ["format", "status", "created_at"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at", "updated_at", "error_message"]


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ["user", "frequency", "format", "report_type", "is_active", "last_sent_at"]
    list_filter = ["frequency", "format", "is_active"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at", "updated_at", "last_sent_at"]
