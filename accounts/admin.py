"""
Admin configuration for accounts app.

PRIVACY NOTE: This admin is intentionally restricted to protect
customer health data privacy. Only essential debugging information
is displayed. Sensitive personal/medical data is hidden.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Profile, UserMedication


class ProfileInline(admin.StackedInline):
    """
    Inline admin for Profile.
    
    PRIVACY: Only shows app settings, not personal/health data.
    """

    model = Profile
    can_delete = False
    verbose_name_plural = "Profile (App Settings Only)"
    
    # Only show app preferences, hide personal/health data
    fields = ["default_timezone", "preferred_score_scale", "onboarding_completed", "onboarding_step"]
    readonly_fields = ["onboarding_completed", "onboarding_step"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin.
    
    PRIVACY: Limited to account status and permissions only.
    Personal details are hidden to protect customer privacy.
    """

    inlines = [ProfileInline]
    # Only show email and account status - no personal names
    list_display = ["email", "is_active", "is_staff", "date_joined"]
    list_filter = ["is_staff", "is_superuser", "is_active"]
    # Only search by email - the unique identifier needed for support
    search_fields = ["email"]
    ordering = ["-date_joined"]
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        # Personal info hidden - not needed for debugging
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    
    # Prevent viewing/editing personal names
    exclude = ["first_name", "last_name"]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Profile admin.
    
    PRIVACY: Shows only app settings and onboarding status.
    Personal data (DOB, age, gender), diagnosis info, and
    medication details are hidden to protect health privacy.
    """

    list_display = ["user_email", "default_timezone", "onboarding_completed", "created_at"]
    search_fields = ["user__email"]
    # Don't filter by health-related fields
    list_filter = ["onboarding_completed", "default_timezone"]
    
    # Only display app settings, not personal/health data
    fields = [
        "user",
        "default_timezone",
        "date_format",
        "preferred_score_scale",
        "onboarding_completed",
        "onboarding_step",
        "created_at",
        "updated_at",
    ]
    readonly_fields = ["user", "created_at", "updated_at"]
    
    def user_email(self, obj):
        """Show user email instead of full user object."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def has_add_permission(self, request):
        # Profiles are created automatically with users
        return False


@admin.register(UserMedication)
class UserMedicationAdmin(admin.ModelAdmin):
    """
    UserMedication admin.
    
    PRIVACY: This model contains sensitive health information.
    Admin access is restricted to existence check only for debugging.
    Actual medication details are hidden.
    """
    
    # Only show that a record exists, not what medication it is
    list_display = ["user_email", "medication_type", "is_current", "updated_at"]
    # Don't allow searching by medication names
    search_fields = ["user__email"]
    list_filter = ["is_current"]
    readonly_fields = ["created_at", "updated_at", "user"]
    
    # Hide medication-specific details - only show metadata
    fields = [
        "user",
        "medication_type",
        "is_current",
        "created_at",
        "updated_at",
    ]
    
    def user_email(self, obj):
        """Show user email for support lookups."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def has_add_permission(self, request):
        # Users manage their own medications through the app
        return False
    
    def has_change_permission(self, request, obj=None):
        # Don't allow editing user health data
        return False
