"""
Admin configuration for notifications app.

PRIVACY NOTE: Notification settings are less sensitive but still
show user behavior patterns. Access is limited to what's needed
for debugging notification delivery issues.
"""

from django.contrib import admin

from .models import PushSubscription, ReminderPreferences, ReminderLog


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    """
    Admin for push subscriptions.
    
    PRIVACY: Only shows subscription status for debugging delivery issues.
    Full endpoint URLs are hidden as they're not needed for debugging.
    """

    list_display = [
        "user_email",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["user__email"]
    readonly_fields = ["user", "created_at", "updated_at", "is_active"]
    
    # Hide the full endpoint URL - just show that a subscription exists
    fields = ["user", "is_active", "created_at", "updated_at"]
    
    def user_email(self, obj):
        """Show user email for support lookups."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def has_add_permission(self, request):
        # Subscriptions are created by the browser
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReminderPreferences)
class ReminderPreferencesAdmin(admin.ModelAdmin):
    """
    Admin for reminder preferences.
    
    PRIVACY: Shows reminder settings for debugging.
    Reminder time could reveal user habits but is needed for
    debugging "why didn't I get my reminder" issues.
    """

    list_display = [
        "user_email",
        "enabled",
        "timezone",
        "updated_at",
    ]
    list_filter = ["enabled"]
    search_fields = ["user__email"]
    readonly_fields = ["user", "created_at", "updated_at"]
    
    fields = ["user", "enabled", "time_of_day", "timezone", "created_at", "updated_at"]
    
    def user_email(self, obj):
        """Show user email for support lookups."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def has_add_permission(self, request):
        # Users set their own preferences
        return False
    
    def has_change_permission(self, request, obj=None):
        # Users manage their own preferences
        return False


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    """
    Admin for reminder logs.
    
    This is primarily for debugging notification delivery.
    Contains minimal personal data.
    """

    list_display = [
        "user_email",
        "date",
        "success",
        "subscriptions_notified",
        "sent_at",
    ]
    list_filter = ["success", "date"]
    search_fields = ["user__email"]
    date_hierarchy = "date"
    ordering = ["-sent_at"]
    readonly_fields = ["user", "date", "success", "subscriptions_notified", "sent_at"]
    
    fields = ["user", "date", "success", "subscriptions_notified", "sent_at"]
    
    def user_email(self, obj):
        """Show user email for support lookups."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow cleanup of old logs
        return True
