"""
Admin configuration for tracking app.

PRIVACY & SECURITY NOTE:
========================
Daily health entries contain SENSITIVE PERSONAL HEALTH INFORMATION (PHI).

This includes:
- Symptom scores (itch, hives)
- Quality of life assessments
- Medication adherence
- Personal notes

Admin access is COMPLETELY RESTRICTED:
- Cannot view any health scores or symptom data
- Cannot view QoL responses
- Cannot view notes
- Cannot view antihistamine usage
- Can only confirm entries exist (for debugging "I logged but it's missing" issues)

Only superusers can see that entries exist for GDPR compliance.
Regular staff CANNOT access health data.
"""

from django.contrib import admin

from .models import DailyEntry


@admin.register(DailyEntry)
class DailyEntryAdmin(admin.ModelAdmin):
    """
    Admin for daily entries.
    
    PRIVACY: ALL health data is COMPLETELY HIDDEN.
    - No symptom scores visible
    - No QoL data visible
    - No notes visible
    - No medication info visible
    
    Only shows that entries exist for debugging purposes.
    """

    # Show ONLY that an entry exists - NO health data
    list_display = [
        "user_email",
        "date",
        "entry_exists",
        "created_at",
    ]
    # NO filtering by any health data
    list_filter = ["date"]
    search_fields = ["user__email"]
    date_hierarchy = "date"
    ordering = ["-date", "-created_at"]
    
    # NO fields shown at all - complete privacy
    fields = []
    readonly_fields = []
    
    # Explicitly exclude ALL health data fields
    exclude = [
        "user",
        "date",
        "score",
        "itch_score",
        "hive_count_score",
        "notes",
        "took_antihistamine",
        "qol_sleep",
        "qol_daily_activities",
        "qol_appearance",
        "qol_mood",
        "created_at",
        "updated_at",
    ]
    
    def user_email(self, obj):
        """Show user email for support lookups."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def entry_exists(self, obj):
        """Show that an entry exists without revealing ANY health data."""
        return True
    entry_exists.short_description = "Entry Recorded"
    entry_exists.boolean = True
    
    def has_add_permission(self, request):
        # Users create their own entries through the app ONLY
        return False
    
    def has_change_permission(self, request, obj=None):
        # NEVER allow editing user health data through admin
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion ONLY for GDPR/data removal requests by superusers
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        # Only superusers can see that entries exist
        # Regular staff cannot access health data at all
        return request.user.is_superuser
    
    def get_queryset(self, request):
        """Limit queryset - extra security layer."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers see nothing
            return qs.none()
        return qs
    
    def get_list_display_links(self, request, list_display):
        """Remove all links to detail view - prevent clicking through."""
        return None
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Block change view entirely - no access to health data details."""
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access to health data details is not permitted.")
    
    def get_actions(self, request):
        """Only allow delete action for GDPR compliance."""
        actions = super().get_actions(request)
        # Keep only delete action, remove others
        return {k: v for k, v in actions.items() if k == 'delete_selected'}
