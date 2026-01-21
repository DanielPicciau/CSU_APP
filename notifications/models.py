"""
Models for push notifications.
"""

from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    """
    Stores Web Push subscription info for a user.
    
    A user can have multiple subscriptions (one per device/browser).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    
    # Web Push subscription data
    endpoint = models.URLField(
        max_length=500,
        help_text="Push service endpoint URL",
    )
    
    # Keys for encryption
    p256dh = models.CharField(
        max_length=100,
        help_text="User public key for encryption",
    )
    
    auth = models.CharField(
        max_length=50,
        help_text="Auth secret for encryption",
    )
    
    # Device info (optional, for user management)
    user_agent = models.CharField(
        max_length=300,
        blank=True,
        default="",
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this subscription is still valid",
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "push subscription"
        verbose_name_plural = "push subscriptions"
        # Unique constraint on endpoint per user
        constraints = [
            models.UniqueConstraint(
                fields=["user", "endpoint"],
                name="unique_user_endpoint",
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"PushSubscription for {self.user.email} - {self.endpoint[:50]}..."


class ReminderPreferences(models.Model):
    """
    User preferences for daily reminder notifications.
    
    One-to-one with User.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reminder_preferences",
    )
    
    enabled = models.BooleanField(
        default=False,
        help_text="Whether daily reminders are enabled",
    )
    
    time_of_day = models.TimeField(
        default="20:00",
        help_text="Time to send reminder (HH:MM)",
    )
    
    timezone = models.CharField(
        max_length=50,
        default="America/New_York",
        help_text="IANA timezone string",
    )
    
    # Guard field to prevent duplicate reminders
    last_reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last reminder sent (for spam prevention)",
    )
    
    last_reminder_date = models.DateField(
        null=True,
        blank=True,
        help_text="The date (in user's timezone) for which last reminder was sent",
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "reminder preferences"
        verbose_name_plural = "reminder preferences"

    def __str__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"Reminders for {self.user.email}: {status} at {self.time_of_day}"


class ReminderLog(models.Model):
    """
    Log of sent reminders to prevent duplicates.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reminder_logs",
    )
    
    date = models.DateField(
        help_text="Date the reminder was for",
    )
    
    sent_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the reminder was sent",
    )
    
    success = models.BooleanField(
        default=True,
        help_text="Whether the push was successfully sent",
    )
    
    subscriptions_notified = models.PositiveIntegerField(
        default=0,
        help_text="Number of subscriptions that were notified",
    )

    class Meta:
        verbose_name = "reminder log"
        verbose_name_plural = "reminder logs"
        ordering = ["-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_user_date_reminder",
            )
        ]

    def __str__(self) -> str:
        return f"Reminder for {self.user.email} on {self.date}"


# Signal to create ReminderPreferences when User is created
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model


@receiver(post_save, sender=get_user_model())
def create_reminder_preferences(sender, instance, created, **kwargs):
    """Create ReminderPreferences when a new User is created."""
    if created:
        ReminderPreferences.objects.get_or_create(user=instance)
