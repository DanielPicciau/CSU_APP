"""
Admin configuration for notifications app.

PRIVACY & SECURITY NOTE:
========================
Notification settings reveal user behavior patterns (when they want reminders).
While less sensitive than health data, access is still limited to:
- Debugging notification delivery issues
- Only superusers can access

Regular staff CANNOT access notification data.
"""

from django.contrib import admin

from .models import PushSubscription, ReminderPreferences, ReminderLog


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    """
    Admin for push subscriptions.
    
    PRIVACY: Only shows subscription status for debugging delivery issues.
    Full endpoint URLs are HIDDEN as they contain device identifiers.
    """

    list_display = [
        "user_email",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["user__email"]
    
    # Hide ALL technical details - just show status
    fields = []
    readonly_fields = []
    exclude = ["user", "endpoint", "auth_key", "p256dh_key", "is_active", "created_at", "updated_at"]
    
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
    
    def has_view_permission(self, request, obj=None):
        # Only superusers can view
        return request.user.is_superuser


@admin.register(ReminderPreferences)
class ReminderPreferencesAdmin(admin.ModelAdmin):
    """
    Admin for reminder preferences.
    
    PRIVACY: Reminder times could reveal user habits/routines.
    Access restricted to superusers only for debugging.
    """

    list_display = [
        "user_email",
        "enabled",
        "timezone",
        "updated_at",
    ]
    list_filter = ["enabled"]
    search_fields = ["user__email"]
    
    # Hide specific times - just show general settings
    fields = []
    readonly_fields = []
    exclude = ["user", "enabled", "time_of_day", "timezone", "created_at", "updated_at"]
    
    def user_email(self, obj):
        """Show user email for support lookups."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def has_add_permission(self, request):
        # Users set their own preferences
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_view_permission(self, request, obj=None):
        # Only superusers can view
        return request.user.is_superuser


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    """
    Admin for reminder logs.
    
    Used for debugging notification delivery issues.
    Access restricted to superusers only.
    """

    list_display = [
        "user_email",
        "date",
        "success",
        "sent_at",
    ]
    list_filter = ["success", "date"]
    search_fields = ["user__email"]
    date_hierarchy = "date"
    ordering = ["-sent_at"]
    
    # Show minimal debug info
    fields = []
    readonly_fields = []
    exclude = ["user", "date", "success", "subscriptions_notified", "sent_at"]
    
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
        # Allow cleanup of old logs - superusers only
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        # Only superusers can view
        return request.user.is_superuser
