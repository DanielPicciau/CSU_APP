"""
App configuration for subscriptions.
"""

from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subscriptions"
    verbose_name = "Cura Premium Subscriptions"

    def ready(self):
        from django.db.models.signals import post_migrate

        from . import signals  # noqa: F401
        from .entitlements import PREMIUM_ENTITLEMENTS
        from .models import SubscriptionPlan

        def ensure_default_plan(sender, **kwargs):
            if sender.name != self.name:
                return
            if not SubscriptionPlan.objects.filter(name__iexact="Premium").exists():
                SubscriptionPlan.objects.create(
                    name="Premium",
                    price_gbp="2.99",
                    billing_period="month",
                    entitlements_json=PREMIUM_ENTITLEMENTS,
                    is_active=True,
                )

        post_migrate.connect(ensure_default_plan, sender=self)
