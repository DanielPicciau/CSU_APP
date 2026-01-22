"""
Subscription models for Cura Premium.

Handles Stripe subscription tracking and premium feature access.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class SubscriptionStatus(models.TextChoices):
    """Stripe subscription status values."""
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past Due"
    UNPAID = "unpaid", "Unpaid"
    CANCELED = "canceled", "Canceled"
    INCOMPLETE = "incomplete", "Incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired", "Incomplete Expired"
    TRIALING = "trialing", "Trialing"
    PAUSED = "paused", "Paused"


class Subscription(models.Model):
    """
    User subscription record for Cura Premium.
    
    Tracks Stripe subscription status and provides premium feature access.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    
    # Stripe identifiers
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe customer ID",
    )
    
    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe subscription ID",
    )
    
    stripe_price_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe price ID for the subscription plan",
    )
    
    # Subscription status
    status = models.CharField(
        max_length=30,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INCOMPLETE,
        help_text="Current subscription status from Stripe",
    )
    
    # Billing dates
    current_period_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Start of current billing period",
    )
    
    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End of current billing period",
    )
    
    cancel_at_period_end = models.BooleanField(
        default=False,
        help_text="Whether subscription will cancel at period end",
    )
    
    canceled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscription was canceled",
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "subscription"
        verbose_name_plural = "subscriptions"
    
    def __str__(self) -> str:
        return f"Subscription for {self.user.email} ({self.status})"
    
    @property
    def is_premium(self) -> bool:
        """Check if user has active premium access."""
        # Active subscription statuses that grant premium access
        active_statuses = [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        ]
        
        # Past due still has access until period ends
        if self.status == SubscriptionStatus.PAST_DUE:
            if self.current_period_end and self.current_period_end > timezone.now():
                return True
        
        return self.status in active_statuses
    
    @property
    def is_canceled_but_active(self) -> bool:
        """Check if subscription is canceled but still in paid period."""
        return (
            self.cancel_at_period_end and 
            self.current_period_end and 
            self.current_period_end > timezone.now()
        )
    
    @property
    def days_remaining(self) -> int | None:
        """Get days remaining in current billing period."""
        if not self.current_period_end:
            return None
        delta = self.current_period_end - timezone.now()
        return max(0, delta.days)


def user_is_premium(user) -> bool:
    """
    Check if a user has premium access.
    
    Returns True if:
    - User has an active subscription
    - User is a superuser (always has premium)
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    try:
        return user.subscription.is_premium
    except Subscription.DoesNotExist:
        return False
