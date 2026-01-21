"""
Web Push utility functions.
"""

import json
import logging
from typing import Any

from django.conf import settings
from pywebpush import webpush, WebPushException

from .models import PushSubscription

logger = logging.getLogger(__name__)


def send_push_notification(
    subscription: PushSubscription,
    title: str,
    body: str,
    url: str | None = None,
    tag: str | None = None,
    data: dict[str, Any] | None = None,
) -> bool:
    """
    Send a Web Push notification to a subscription.
    
    Returns True if successful, False otherwise.
    If the subscription is no longer valid, it will be marked inactive.
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.warning("VAPID keys not configured, skipping push notification")
        return False

    payload = {
        "title": title,
        "body": body,
        "icon": "/static/icons/icon-192x192.png",
        "badge": "/static/icons/badge-72x72.png",
        "tag": tag or "csu-tracker",
        "data": {
            "url": url or "/",
            **(data or {}),
        },
    }

    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }

    vapid_claims = {
        "sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}",
    }

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=vapid_claims,
        )
        logger.info(f"Push sent successfully to {subscription.user.email}")
        return True

    except WebPushException as e:
        logger.error(f"Push failed for {subscription.user.email}: {e}")
        
        # If subscription is gone (410) or invalid (404), mark as inactive
        if e.response and e.response.status_code in (404, 410):
            subscription.is_active = False
            subscription.save()
            logger.info(f"Subscription marked inactive for {subscription.user.email}")
        
        return False


def send_push_to_user(
    user,
    title: str,
    body: str,
    url: str | None = None,
    tag: str | None = None,
    data: dict[str, Any] | None = None,
) -> int:
    """
    Send a push notification to all active subscriptions for a user.
    
    Returns the number of successfully sent notifications.
    """
    subscriptions = PushSubscription.objects.filter(
        user=user,
        is_active=True,
    )
    
    success_count = 0
    for subscription in subscriptions:
        if send_push_notification(
            subscription=subscription,
            title=title,
            body=body,
            url=url,
            tag=tag,
            data=data,
        ):
            success_count += 1
    
    return success_count
