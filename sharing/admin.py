"""
Admin configuration for sharing models.
"""

from django.contrib import admin

from .models import SharingContactAccess


@admin.register(SharingContactAccess)
class SharingContactAccessAdmin(admin.ModelAdmin):
    list_display = ["owner_user", "contact_email", "role", "created_at", "revoked_at"]
    list_filter = ["role", "revoked_at"]
    search_fields = ["owner_user__email", "contact_email"]
    readonly_fields = ["created_at", "access_token"]
