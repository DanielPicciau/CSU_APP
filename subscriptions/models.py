"""
Subscription models for Cura Premium.

Handles Stripe subscription tracking and premium feature access.
"""

from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """Subscription plan definition with entitlement configuration."""

    BILLING_PERIOD_CHOICES = [
        ("month", "Monthly"),
        ("year", "Yearly"),
    ]

    name = models.CharField(max_length=100, unique=True)
    price_gbp = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Plan price in GBP",
    )
    billing_period = models.CharField(
        max_length=20,
        choices=BILLING_PERIOD_CHOICES,
        default="month",
    )
    entitlements_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Entitlements map for this plan",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "subscription plan"
        verbose_name_plural = "subscription plans"
        db_table = "subscriptions_plan"

    def __str__(self) -> str:
        return f"{self.name} ({self.billing_period})"

    @classmethod
    def get_default_plan(cls):
        """Return the primary paid plan if configured."""
        return cls.objects.filter(is_active=True).order_by("id").first()


class EntitlementOverride(models.Model):
    """Per-user entitlement overrides with optional expiry."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entitlement_overrides",
    )
    entitlement_key = models.CharField(max_length=100)
    value = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entitlement_overrides_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "entitlement override"
        verbose_name_plural = "entitlement overrides"
        db_table = "subscriptions_entitlement_override"
        indexes = [
            models.Index(fields=["user", "entitlement_key"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} override {self.entitlement_key}={self.value}"

    @property
    def is_active(self) -> bool:
        """Return True if the override is currently active."""
        if self.expires_at is None:
            return True
        return self.expires_at > timezone.now()


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

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
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

    grace_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End of grace period after failed payment",
    )

    trial_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End of trial period if applicable",
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
    def normalized_status(self) -> str:
        """Map provider status to normalized subscription status."""
        if self.status == SubscriptionStatus.TRIALING:
            return "trialing"
        if self.status == SubscriptionStatus.ACTIVE:
            return "active"
        if self.status == SubscriptionStatus.PAST_DUE:
            if self.grace_period_end and self.grace_period_end > timezone.now():
                return "grace"
            return "past_due"
        if self.status == SubscriptionStatus.CANCELED:
            return "canceled"
        if self.status in {SubscriptionStatus.UNPAID, SubscriptionStatus.INCOMPLETE_EXPIRED}:
            return "expired"
        return "past_due"

    @property
    def is_in_paid_period(self) -> bool:
        """Check if current period end is still in the future."""
        return bool(self.current_period_end and self.current_period_end > timezone.now())

    @property
    def is_in_grace_period(self) -> bool:
        """Check if subscription is within grace period."""
        return bool(self.grace_period_end and self.grace_period_end > timezone.now())

    @property
    def is_premium(self) -> bool:
        """Check if user has active premium access."""
        # Active subscription statuses that grant premium access
        active_statuses = {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        }

        if self.status in active_statuses:
            return True

        # Past due still has access during grace or paid period
        if self.status == SubscriptionStatus.PAST_DUE:
            return self.is_in_grace_period or self.is_in_paid_period

        # Allow access until period end when canceling
        if self.cancel_at_period_end and self.is_in_paid_period:
            return True

        return False
    
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

    def set_grace_period(self, grace_days: int) -> None:
        """Set grace period end relative to now."""
        self.grace_period_end = timezone.now() + timedelta(days=grace_days)


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

    from .entitlements import has_entitlement
    return has_entitlement(user, "premium_access")
