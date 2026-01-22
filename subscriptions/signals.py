"""
Signal handlers for subscription entitlements.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from audit.utils import log_event
from .entitlements import invalidate_entitlements_cache
from .models import EntitlementOverride, Subscription


@receiver(post_save, sender=Subscription)
@receiver(post_delete, sender=Subscription)
def subscription_changed(sender, instance, **kwargs):
    """Invalidate cached entitlements when subscription changes."""
    invalidate_entitlements_cache(instance.user_id)


@receiver(post_save, sender=EntitlementOverride)
def entitlement_override_saved(sender, instance, created, **kwargs):
    """Invalidate cached entitlements when overrides change."""
    invalidate_entitlements_cache(instance.user_id)
    log_event(
        action="entitlement_override_created" if created else "entitlement_override_updated",
        target_type="entitlement_override",
        target_id=instance.id,
        actor=instance.created_by,
        metadata={
            "user_id": instance.user_id,
            "entitlement_key": instance.entitlement_key,
            "value": instance.value,
            "expires_at": instance.expires_at.isoformat() if instance.expires_at else None,
            "reason": instance.reason,
        },
    )


@receiver(post_delete, sender=EntitlementOverride)
def entitlement_override_deleted(sender, instance, **kwargs):
    """Invalidate cached entitlements when overrides are removed."""
    invalidate_entitlements_cache(instance.user_id)
    log_event(
        action="entitlement_override_deleted",
        target_type="entitlement_override",
        target_id=instance.id,
        actor=instance.created_by,
        metadata={
            "user_id": instance.user_id,
            "entitlement_key": instance.entitlement_key,
        },
    )
