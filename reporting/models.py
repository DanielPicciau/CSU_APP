"""
Models for export jobs and report scheduling.
"""

from datetime import timedelta
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ExportFormat(models.TextChoices):
    PDF = "pdf", "PDF"
    CSV = "csv", "CSV"
    XLSX = "xlsx", "Excel"


class ExportJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


def export_job_upload_path(instance, filename: str) -> str:
    """Store exports under user/date based paths."""
    date_segment = timezone.now().strftime("%Y/%m/%d")
    token = uuid.uuid4().hex
    return f"exports/user_{instance.user_id}/{date_segment}/{token}_{filename}"


class ExportJob(models.Model):
    """Background export job for multi-format reporting."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="export_jobs",
    )
    format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.PDF,
    )
    from_date = models.DateField()
    to_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=ExportJobStatus.choices,
        default=ExportJobStatus.PENDING,
    )
    file = models.FileField(
        upload_to=export_job_upload_path,
        null=True,
        blank=True,
    )
    file_url = models.URLField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    options_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "export job"
        verbose_name_plural = "export jobs"
        db_table = "reporting_export_job"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Export {self.id} for {self.user.email} ({self.status})"

    def mark_completed(self, file_url: str | None = None) -> None:
        """Mark job as completed and set expiry."""
        self.status = ExportJobStatus.COMPLETED
        if file_url:
            self.file_url = file_url
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        self.save(update_fields=["status", "file_url", "expires_at", "updated_at"])

    def mark_failed(self, message: str) -> None:
        """Mark job as failed with error details."""
        self.status = ExportJobStatus.FAILED
        self.error_message = message
        self.save(update_fields=["status", "error_message", "updated_at"])


class ReportFrequency(models.TextChoices):
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class ReportSchedule(models.Model):
    """User-configured schedule for automatic report exports."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_schedules",
    )
    frequency = models.CharField(
        max_length=20,
        choices=ReportFrequency.choices,
        default=ReportFrequency.WEEKLY,
    )
    timezone = models.CharField(max_length=50, default="UTC")
    format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.PDF,
    )
    report_type = models.CharField(max_length=20, default="quick")
    last_sent_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "report schedule"
        verbose_name_plural = "report schedules"
        db_table = "reporting_report_schedule"
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} {self.frequency} schedule"
