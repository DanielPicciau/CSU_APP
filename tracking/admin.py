"""
Admin configuration for tracking app.

PRIVACY NOTE: Daily health entries contain sensitive personal
health information. Admin access is restricted to metadata only
for debugging purposes (e.g., checking if entries exist).
"""

from django.contrib import admin

from .models import DailyEntry


@admin.register(DailyEntry)
class DailyEntryAdmin(admin.ModelAdmin):
    """
    Admin for daily entries.
    
    PRIVACY: Health scores and notes are hidden.
    Only shows that entries exist for debugging purposes.
    """

    # Only show metadata - hide actual health scores
    list_display = [
        "user_email",
        "date",
        "has_entry",
        "created_at",
    ]
    # Don't filter by health data
    list_filter = ["date"]
    search_fields = ["user__email"]
    date_hierarchy = "date"
    ordering = ["-date", "-created_at"]
    readonly_fields = ["user", "date", "created_at", "updated_at"]
    
    # Only show metadata, not health data
    fields = [
        "user",
        "date",
        "created_at",
        "updated_at",
    ]
    
    def user_email(self, obj):
        """Show user email for support lookups."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def has_entry(self, obj):
        """Show that an entry exists without revealing the score."""
        return True
    has_entry.short_description = "Entry Recorded"
    has_entry.boolean = True
    
    def has_add_permission(self, request):
        # Users create their own entries through the app
        return False
    
    def has_change_permission(self, request, obj=None):
        # Don't allow editing user health data
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion for GDPR/data removal requests
        return True
