"""
Admin configuration for Cura Premium subscriptions.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import EntitlementOverride, Subscription, SubscriptionPlan, SubscriptionStatus


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price_gbp", "billing_period", "is_active", "updated_at"]
    list_filter = ["billing_period", "is_active"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(EntitlementOverride)
class EntitlementOverrideAdmin(admin.ModelAdmin):
    list_display = ["user", "entitlement_key", "value", "expires_at", "created_at"]
    list_filter = ["entitlement_key", "value"]
    search_fields = ["user__email", "entitlement_key", "reason"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    Admin for managing Cura Premium subscriptions.
    
    Allows viewing subscription status and manually adjusting
    subscriptions when needed (e.g., for support cases).
    """
    
    list_display = [
        "user_email",
        "plan",
        "status_badge",
        "current_period_end",
        "cancel_at_period_end",
        "created_at",
    ]
    
    list_filter = [
        "status",
        "plan",
        "cancel_at_period_end",
        "created_at",
    ]
    
    search_fields = [
        "user__email",
        "stripe_customer_id",
        "stripe_subscription_id",
    ]
    
    readonly_fields = [
        "stripe_customer_id",
        "stripe_subscription_id",
        "stripe_price_id",
        "current_period_start",
        "current_period_end",
        "grace_period_end",
        "trial_end",
        "canceled_at",
        "created_at",
        "updated_at",
    ]
    
    fieldsets = (
        ("User", {
            "fields": ("user",),
        }),
        ("Plan", {
            "fields": ("plan",),
        }),
        ("Stripe Details", {
            "fields": (
                "stripe_customer_id",
                "stripe_subscription_id",
                "stripe_price_id",
            ),
            "classes": ("collapse",),
        }),
        ("Subscription Status", {
            "fields": (
                "status",
                "cancel_at_period_end",
            ),
        }),
        ("Billing Period", {
            "fields": (
                "current_period_start",
                "current_period_end",
                "grace_period_end",
                "trial_end",
                "canceled_at",
            ),
        }),
        ("Metadata", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"
    
    def status_badge(self, obj):
        """Display status with colored badge."""
        colors = {
            SubscriptionStatus.ACTIVE: "#22C55E",
            SubscriptionStatus.TRIALING: "#3B82F6",
            SubscriptionStatus.PAST_DUE: "#F59E0B",
            SubscriptionStatus.CANCELED: "#EF4444",
            SubscriptionStatus.UNPAID: "#EF4444",
            SubscriptionStatus.INCOMPLETE: "#9CA3AF",
            SubscriptionStatus.INCOMPLETE_EXPIRED: "#9CA3AF",
            SubscriptionStatus.PAUSED: "#8B5CF6",
        }
        color = colors.get(obj.status, "#9CA3AF")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"
    
    def has_delete_permission(self, request, obj=None):
        """Prevent accidental deletion of subscription records."""
        return request.user.is_superuser
