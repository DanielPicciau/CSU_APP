"""
Admin configuration for backups.
"""

from django.contrib import admin

from .models import BackupSnapshot


@admin.register(BackupSnapshot)
class BackupSnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at", "updated_at", "error_message"]
