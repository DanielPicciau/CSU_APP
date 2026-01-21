"""
Serializers for the tracking app.
"""

from datetime import date, timedelta

from django.conf import settings
from rest_framework import serializers

from .models import DailyEntry


class DailyEntrySerializer(serializers.ModelSerializer):
    """Serializer for daily CSU entries."""

    class Meta:
        model = DailyEntry
        fields = [
            "id",
            "date",
            "score",
            "itch_score",
            "hive_count_score",
            "notes",
            "took_antihistamine",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_date(self, value):
        """Prevent future dates."""
        if value > date.today():
            raise serializers.ValidationError("Cannot create entries for future dates.")
        return value

    def validate_score(self, value):
        """Validate score against max."""
        max_score = settings.CSU_MAX_SCORE
        if value > max_score:
            raise serializers.ValidationError(f"Score cannot exceed {max_score}.")
        return value

    def validate(self, attrs):
        """Ensure unique entry per user per date."""
        user = self.context["request"].user
        entry_date = attrs.get("date")
        
        # For updates, exclude the current instance
        instance = self.instance
        query = DailyEntry.objects.filter(user=user, date=entry_date)
        if instance:
            query = query.exclude(pk=instance.pk)
        
        if query.exists():
            raise serializers.ValidationError(
                {"date": "An entry for this date already exists."}
            )
        
        return attrs


class DailyEntryCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating daily entries with upsert support."""

    class Meta:
        model = DailyEntry
        fields = [
            "date",
            "score",
            "itch_score",
            "hive_count_score",
            "notes",
            "took_antihistamine",
        ]

    def validate_score(self, value):
        """Validate score against max."""
        max_score = settings.CSU_MAX_SCORE
        if value > max_score:
            raise serializers.ValidationError(f"Score cannot exceed {max_score}.")
        return value


class AdherenceMetricsSerializer(serializers.Serializer):
    """Serializer for adherence metrics response."""

    period_days = serializers.IntegerField()
    entries_count = serializers.IntegerField()
    adherence_percentage = serializers.FloatField()
    average_score = serializers.FloatField(allow_null=True)
    missing_dates = serializers.ListField(child=serializers.DateField())


class WeeklyStatsSerializer(serializers.Serializer):
    """Serializer for weekly statistics (UAS7)."""

    week_start = serializers.DateField()
    week_end = serializers.DateField()
    uas7_score = serializers.IntegerField()
    entries_count = serializers.IntegerField()
    complete = serializers.BooleanField()
