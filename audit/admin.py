"""
Admin configuration for audit logs.
"""

from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "target_type", "target_id", "actor", "created_at"]
    list_filter = ["action", "target_type", "created_at"]
    search_fields = ["action", "target_type", "target_id", "actor__email"]
    readonly_fields = ["created_at", "metadata_json"]
