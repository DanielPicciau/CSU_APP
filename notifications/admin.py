"""
Admin configuration for notifications app.
"""

from django.contrib import admin

from .models import PushSubscription, ReminderPreferences, ReminderLog


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    """Admin for push subscriptions."""

    list_display = [
        "user",
        "endpoint_short",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["user__email", "endpoint"]
    readonly_fields = ["created_at", "updated_at"]
    
    def endpoint_short(self, obj):
        """Truncate endpoint for display."""
        return obj.endpoint[:60] + "..."
    endpoint_short.short_description = "Endpoint"


@admin.register(ReminderPreferences)
class ReminderPreferencesAdmin(admin.ModelAdmin):
    """Admin for reminder preferences."""

    list_display = [
        "user",
        "enabled",
        "time_of_day",
        "timezone",
        "updated_at",
    ]
    list_filter = ["enabled", "timezone"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    """Admin for reminder logs."""

    list_display = [
        "user",
        "date",
        "success",
        "subscriptions_notified",
        "sent_at",
    ]
    list_filter = ["success", "date"]
    search_fields = ["user__email"]
    date_hierarchy = "date"
    ordering = ["-sent_at"]
