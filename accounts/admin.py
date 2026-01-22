"""
Admin configuration for accounts app.

PRIVACY & SECURITY NOTE:
========================
This admin is STRICTLY LIMITED to protect user health data privacy.
CSU Tracker handles sensitive personal health information (PHI) including:
- Medical diagnoses
- Medications
- Symptom tracking data
- Quality of life assessments

Admins can ONLY see:
- Email addresses (for support/account issues)
- Account status (active/inactive, permissions)
- App settings (timezone, preferences)

Admins CANNOT see:
- Personal details (name, DOB, age, gender)
- Health information (diagnoses, medications, symptoms)
- Any medical data whatsoever

This complies with healthcare data protection principles (GDPR, HIPAA-like).
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Profile, UserMedication


class ProfileInline(admin.StackedInline):
    """
    Inline admin for Profile.
    
    PRIVACY: Only shows app settings, NO personal/health data.
    """

    model = Profile
    can_delete = False
    verbose_name_plural = "Profile (App Settings Only)"
    
    # ONLY app preferences - NO personal or health data
    fields = ["default_timezone", "preferred_score_scale", "onboarding_completed"]
    readonly_fields = ["onboarding_completed"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin.
    
    PRIVACY: Limited to account status and permissions only.
    Personal details are COMPLETELY HIDDEN to protect customer privacy.
    """

    inlines = [ProfileInline]
    # Only show email and account status - NO personal names
    list_display = ["email", "is_active", "is_staff", "date_joined"]
    list_filter = ["is_staff", "is_superuser", "is_active"]
    # Only search by email - the unique identifier needed for support
    search_fields = ["email"]
    ordering = ["-date_joined"]
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        # Personal info HIDDEN - not needed and protects privacy
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
    
    # COMPLETELY PREVENT viewing/editing personal names
    exclude = ["first_name", "last_name", "username"]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Profile admin.
    
    PRIVACY: Shows ONLY app settings and onboarding status.
    ALL personal data (DOB, age, gender) and health data 
    (diagnosis, medication status) are COMPLETELY HIDDEN.
    """

    list_display = ["user_email", "default_timezone", "onboarding_completed", "created_at"]
    search_fields = ["user__email"]
    # NO filtering by health-related fields
    list_filter = ["onboarding_completed", "default_timezone"]
    
    # ONLY display app settings - NO personal or health data
    fields = [
        "user",
        "default_timezone",
        "date_format",
        "preferred_score_scale",
        "onboarding_completed",
        "created_at",
        "updated_at",
    ]
    readonly_fields = ["user", "created_at", "updated_at", "onboarding_completed"]
    
    # Explicitly exclude ALL sensitive fields
    exclude = [
        # Personal data
        "display_name",
        "date_of_birth",
        "age",
        "gender",
        # Health data
        "csu_diagnosis",
        "has_prescribed_medication",
        # Internal
        "onboarding_step",
        "allow_data_collection",
        "privacy_consent_given",
        "privacy_consent_date",
        "account_deletion_requested",
    ]
    
    def user_email(self, obj):
        """Show user email instead of full user object."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def has_add_permission(self, request):
        # Profiles are created automatically with users
        return False
    
    def has_change_permission(self, request, obj=None):
        # Prevent any changes to profiles through admin
        return False


@admin.register(UserMedication)
class UserMedicationAdmin(admin.ModelAdmin):
    """
    UserMedication admin.
    
    PRIVACY: This model contains SENSITIVE HEALTH INFORMATION.
    
    Admin access is COMPLETELY RESTRICTED:
    - Cannot view medication details
    - Cannot add/edit/delete medications
    - Only shows aggregate count for debugging
    
    Users manage their own medications through the app ONLY.
    """
    
    # Show ONLY that records exist for a user - NO medication details
    list_display = ["user_email", "record_exists", "updated_at"]
    # Only search by email - NO medication search
    search_fields = ["user__email"]
    # NO filtering by any health data
    list_filter = []
    
    # NO fields shown - medications are completely private
    fields = []
    readonly_fields = []
    exclude = [
        "user",
        "medication_key",
        "custom_name",
        "medication_type",
        "dose_amount",
        "dose_unit",
        "frequency_per_day",
        "last_injection_date",
        "injection_frequency",
        "is_current",
        "created_at",
        "updated_at",
    ]
    
    def user_email(self, obj):
        """Show user email for support lookups."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def record_exists(self, obj):
        """Indicate that a medication record exists without revealing details."""
        return True
    record_exists.short_description = "Has Medication Record"
    record_exists.boolean = True
    
    def has_add_permission(self, request):
        # Users manage their own medications through the app
        return False
    
    def has_change_permission(self, request, obj=None):
        # NEVER allow editing user health data
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Allow deletion ONLY for GDPR/data removal requests
        # This should be done through a formal process
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        # Only superusers can see that records exist (for GDPR compliance)
        # Even then, they cannot see medication details
        return request.user.is_superuser
    
    def get_list_display_links(self, request, list_display):
        """Remove all links to detail view - prevent clicking through."""
        return None
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Block change view entirely."""
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Access to medication details is not permitted.")
    
    def get_actions(self, request):
        """Only allow delete action for GDPR compliance."""
        actions = super().get_actions(request)
        # Keep only delete action, remove others
        return {k: v for k, v in actions.items() if k == 'delete_selected'}
