"""
Tasks for account management and data retention.
"""

from datetime import timedelta
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

logger = logging.getLogger("django")
User = get_user_model()

@shared_task
def purge_inactive_accounts() -> str:
    """
    Permanently delete accounts that were marked for deletion > 30 days ago.
    This enforces the storage limitation principle of GDPR.
    """
    cutoff = timezone.now() - timedelta(days=30)
    
    # Filter users whose profile has account_deletion_requested set > 30 days ago
    # We query Profile related to User
    users_to_delete = User.objects.filter(
        profile__account_deletion_requested__lt=cutoff
    )
    
    count = users_to_delete.count()
    if count > 0:
        logger.info(f"Purging {count} inactive accounts...")
        # Delete using standard Django delete to cascade
        users_to_delete.delete()
        
    return f"Purged {count} accounts"
