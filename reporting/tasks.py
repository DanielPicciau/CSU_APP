"""
Celery tasks for reporting exports and schedules.
"""

from datetime import timedelta

import pytz
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from subscriptions.entitlements import has_entitlement
from tracking.exports import CSUExporter

from .models import (
    ExportFormat,
    ExportJob,
    ExportJobStatus,
    ReportFrequency,
    ReportSchedule,
)


@shared_task
def process_export_job(job_id: int) -> str:
    """Generate an export file for a queued job."""
    try:
        job = ExportJob.objects.select_related("user").get(id=job_id)
    except ExportJob.DoesNotExist:
        return "missing_job"

    if job.status not in {ExportJobStatus.PENDING, ExportJobStatus.PROCESSING}:
        return f"skipped_{job.status}"

    job.status = ExportJobStatus.PROCESSING
    job.save(update_fields=["status", "updated_at"])

    try:
        options = job.options_json or {}
        exporter = CSUExporter(job.user, job.from_date, job.to_date, options)

        if job.format == ExportFormat.CSV:
            response = exporter.export_csv()
            content = response.content
            ext = "csv"
        elif job.format == ExportFormat.PDF:
            response = exporter.export_pdf()
            content = response.content
            ext = "pdf"
        else:
            job.mark_failed("XLSX export not implemented yet.")
            return "unsupported_format"

        filename = f"csu_report_{job.user_id}_{job.from_date:%Y%m%d}_{job.to_date:%Y%m%d}.{ext}"
        job.file.save(filename, ContentFile(content), save=False)
        job.file_url = job.file.url if job.file else ""
        job.status = ExportJobStatus.COMPLETED
        job.expires_at = timezone.now() + timedelta(days=7)
        job.save()
        return "completed"
    except Exception as exc:
        job.mark_failed(str(exc))
        return "failed"


@shared_task
def enqueue_scheduled_reports() -> int:
    """Enqueue export jobs for active schedules that are due."""
    now = timezone.now()
    scheduled = 0

    schedules = ReportSchedule.objects.select_related("user").filter(is_active=True)
    for schedule in schedules:
        user = schedule.user

        if not has_entitlement(user, "scheduled_reports"):
            continue

        tz = pytz.timezone(schedule.timezone)
        local_now = now.astimezone(tz)
        last_sent = schedule.last_sent_at.astimezone(tz) if schedule.last_sent_at else None

        from_date = None
        to_date = None
        due = False

        if schedule.frequency == ReportFrequency.WEEKLY:
            due = not last_sent or last_sent.date() <= (local_now.date() - timedelta(days=7))
            from_date = local_now.date() - timedelta(days=6)
            to_date = local_now.date()
        elif schedule.frequency == ReportFrequency.MONTHLY:
            due = not last_sent or last_sent.month != local_now.month or last_sent.year != local_now.year
            from_date = local_now.date().replace(day=1)
            to_date = local_now.date()

        if not due:
            continue

        if schedule.report_type == "detailed" and not has_entitlement(user, "reports_advanced"):
            continue

        job = ExportJob.objects.create(
            user=user,
            format=schedule.format,
            from_date=from_date,
            to_date=to_date,
            status=ExportJobStatus.PENDING,
            options_json={"report_type": schedule.report_type},
        )
        process_export_job.delay(job.id)
        schedule.last_sent_at = now
        schedule.save(update_fields=["last_sent_at", "updated_at"])
        scheduled += 1

    return scheduled
