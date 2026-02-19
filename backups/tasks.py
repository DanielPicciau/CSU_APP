"""
Celery tasks for encrypted cloud backups.
"""

import json
from datetime import timedelta

from celery import shared_task
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from accounts.models import Profile
from subscriptions.entitlements import has_entitlement
from tracking.models import DailyEntry

from .models import BackupSnapshot, BackupStatus


def _get_fernet() -> tuple[Fernet, int]:
    """Return active Fernet key and index for encryption."""
    key = settings.FERNET_KEYS[0]
    key_bytes = key.encode() if isinstance(key, str) else key
    return Fernet(key_bytes), 0


@shared_task
def create_backup_snapshot(user_id: int) -> str:
    """Create an encrypted backup snapshot for a user."""
    snapshot = BackupSnapshot.objects.create(user_id=user_id, status=BackupStatus.PENDING)

    try:
        entries = list(
            DailyEntry.objects.filter(user_id=user_id).values(
                "date",
                "score",
                "itch_score",
                "hive_count_score",
                "notes",
                "took_antihistamine",
                "qol_sleep",
                "qol_daily_activities",
                "qol_appearance",
                "qol_mood",
                "created_at",
                "updated_at",
            ).iterator(chunk_size=500)
        )
        profile = Profile.objects.filter(user_id=user_id).values(
            "display_name",
            "date_of_birth",
            "age",
            "gender",
            "csu_diagnosis",
            "has_prescribed_medication",
            "default_timezone",
            "preferred_score_scale",
            "created_at",
            "updated_at",
        ).first()

        payload = {
            "user_id": user_id,
            "generated_at": timezone.now().isoformat(),
            "profile": profile,
            "entries": entries,
        }

        serialized = json.dumps(payload, default=str).encode("utf-8")
        fernet, key_index = _get_fernet()
        encrypted = fernet.encrypt(serialized)

        filename = f"csu_backup_{user_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.json.enc"
        snapshot.file.save(filename, ContentFile(encrypted), save=False)
        snapshot.storage_path = snapshot.file.name
        snapshot.encryption_metadata = {
            "method": "fernet",
            "key_index": key_index,
        }
        snapshot.status = BackupStatus.COMPLETED
        snapshot.save()
        return "completed"
    except Exception as exc:
        snapshot.status = BackupStatus.FAILED
        snapshot.error_message = str(exc)
        snapshot.save()
        return "failed"


@shared_task
def enqueue_nightly_backups() -> int:
    """Schedule nightly backups for premium users."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    processed = 0

    for user in User.objects.filter(is_active=True).only("id"):
        if not has_entitlement(user, "cloud_backup"):
            continue
        create_backup_snapshot.delay(user.id)
        processed += 1

    return processed
