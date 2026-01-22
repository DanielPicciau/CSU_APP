"""
Models for secure sharing and access control.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SharingRole(models.TextChoices):
    VIEW = "view", "View"
    EDIT = "edit", "Edit"
    ADMIN = "admin", "Admin"


class SharingContactAccess(models.Model):
    """Access grants for sharing reports/exports with contacts."""

    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sharing_contacts",
    )
    contact_email = models.EmailField()
    role = models.CharField(
        max_length=10,
        choices=SharingRole.choices,
        default=SharingRole.VIEW,
    )
    access_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    resource_type = models.CharField(max_length=50, blank=True, default="")
    resource_id = models.CharField(max_length=100, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "sharing access"
        verbose_name_plural = "sharing access"
        db_table = "sharing_contact_access"
        indexes = [
            models.Index(fields=["owner_user", "contact_email"]),
            models.Index(fields=["access_token"]),
        ]

    def __str__(self) -> str:
        return f"{self.owner_user.email} -> {self.contact_email} ({self.role})"

    @property
    def is_active(self) -> bool:
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True
