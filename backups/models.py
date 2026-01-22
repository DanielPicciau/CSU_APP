"""
Models for user backup snapshots.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class BackupStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


def backup_upload_path(instance, filename: str) -> str:
    """Store backups under user/date based paths."""
    date_segment = timezone.now().strftime("%Y/%m/%d")
    token = uuid.uuid4().hex
    return f"backups/user_{instance.user_id}/{date_segment}/{token}_{filename}"


class BackupSnapshot(models.Model):
    """Encrypted snapshot of user data for restore."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="backup_snapshots",
    )
    status = models.CharField(
        max_length=20,
        choices=BackupStatus.choices,
        default=BackupStatus.PENDING,
    )
    file = models.FileField(
        upload_to=backup_upload_path,
        null=True,
        blank=True,
    )
    storage_path = models.CharField(max_length=500, blank=True, default="")
    encryption_metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "backup snapshot"
        verbose_name_plural = "backup snapshots"
        db_table = "backups_snapshot"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"Backup {self.id} for {self.user.email} ({self.status})"
