"""
Serializers for the notifications app.
"""

import time

from django.db import OperationalError
from rest_framework import serializers

from .models import PushSubscription, ReminderPreferences


class PushSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for push subscriptions."""

    class Meta:
        model = PushSubscription
        fields = ["id", "endpoint", "p256dh", "auth", "user_agent", "is_active", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]


class PushSubscriptionCreateSerializer(serializers.Serializer):
    """Serializer for creating a push subscription from browser format."""

    endpoint = serializers.URLField(max_length=500)
    keys = serializers.DictField(child=serializers.CharField())

    def validate_keys(self, value):
        """Ensure required keys are present."""
        if "p256dh" not in value or "auth" not in value:
            raise serializers.ValidationError(
                "Keys must contain 'p256dh' and 'auth'"
            )
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        keys = validated_data.pop("keys")
        user_agent = self.context["request"].META.get("HTTP_USER_AGENT", "")
        
        # Retry logic for SQLite database locks
        max_retries = 3
        for attempt in range(max_retries):
            try:
                subscription, created = PushSubscription.objects.update_or_create(
                    user=user,
                    endpoint=validated_data["endpoint"],
                    defaults={
                        "p256dh": keys["p256dh"],
                        "auth": keys["auth"],
                        "user_agent": user_agent[:300],
                        "is_active": True,
                    },
                )
                return subscription
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                raise


class ReminderPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for reminder preferences."""

    class Meta:
        model = ReminderPreferences
        fields = ["enabled", "time_of_day", "timezone", "updated_at"]
        read_only_fields = ["updated_at"]
