"""
Admin configuration for tracking app.
"""

from django.contrib import admin

from .models import DailyEntry


@admin.register(DailyEntry)
class DailyEntryAdmin(admin.ModelAdmin):
    """Admin for daily entries."""

    list_display = [
        "user",
        "date",
        "score",
        "itch_score",
        "hive_count_score",
        "took_antihistamine",
        "created_at",
    ]
    list_filter = ["date", "took_antihistamine", "score"]
    search_fields = ["user__email", "notes"]
    date_hierarchy = "date"
    ordering = ["-date", "-created_at"]
    readonly_fields = ["created_at", "updated_at"]
    
    fieldsets = (
        (None, {
            "fields": ("user", "date", "score"),
        }),
        ("Component Scores", {
            "fields": ("itch_score", "hive_count_score"),
        }),
        ("Additional Info", {
            "fields": ("notes", "took_antihistamine"),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
