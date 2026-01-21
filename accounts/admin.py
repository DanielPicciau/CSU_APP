"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Profile, UserMedication


class ProfileInline(admin.StackedInline):
    """Inline admin for Profile."""

    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin."""

    inlines = [ProfileInline]
    list_display = ["email", "first_name", "last_name", "is_staff", "date_joined"]
    list_filter = ["is_staff", "is_superuser", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
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


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Profile admin."""

    list_display = ["user", "default_timezone", "onboarding_completed", "created_at"]
    search_fields = ["user__email"]
    list_filter = ["default_timezone", "onboarding_completed", "has_prescribed_medication"]


@admin.register(UserMedication)
class UserMedicationAdmin(admin.ModelAdmin):
    """
    UserMedication admin.
    
    Note: This displays user-reported contextual data only.
    Not medical records or prescriptions.
    """
    
    list_display = ["user", "display_name", "medication_type", "is_current", "updated_at"]
    search_fields = ["user__email", "medication_key", "custom_name"]
    list_filter = ["medication_type", "is_current"]
    readonly_fields = ["created_at", "updated_at"]
    
    fieldsets = (
        ("User", {"fields": ("user",)}),
        ("Medication Info", {"fields": ("medication_key", "custom_name", "medication_type")}),
        ("Antihistamine Context (Optional)", {
            "fields": ("dose_amount", "dose_unit", "frequency_per_day"),
            "classes": ("collapse",),
        }),
        ("Injectable Context (Optional)", {
            "fields": ("last_injection_date", "injection_frequency"),
            "classes": ("collapse",),
        }),
        ("Status", {"fields": ("is_current", "created_at", "updated_at")}),
    )
