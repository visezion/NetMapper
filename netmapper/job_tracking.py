"""Helpers to reconcile queued scan jobs with NetBox/RQ state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from core.models import Job as CoreJob
from rq.exceptions import NoSuchJobError
from rq.job import Job as RQJob
import django_rq

from netmapper.models import NetworkScanStatusChoices

ACTIVE_SCAN_STATUSES = {
    NetworkScanStatusChoices.QUEUED,
    NetworkScanStatusChoices.RUNNING,
}
ACTIVE_CORE_JOB_STATUSES = {"pending", "scheduled", "running"}
FAILED_CORE_JOB_STATUSES = {"failed", "errored"}


@dataclass(frozen=True)
class ScanJobHealth:
    """Current state of the background job behind a saved scan record."""

    core_status: str | None
    queue_status: str | None
    queue_name: str
    should_mark_failed: bool
    error_message: str
    detail_message: str


def build_orphaned_job_error(job_id, queue_name):
    """Return a troubleshooting message for stale jobs missing from the queue."""
    return (
        f"Background scan job {job_id} is no longer present in the {queue_name!r} "
        "queue, but NetBox still marks it as running. This usually means the worker "
        "or deployment restarted while the scan was in progress. Re-run the scan."
    )


def evaluate_scan_job_health(
    *,
    record_status,
    job_id,
    started_at,
    core_status=None,
    core_error="",
    queue_status=None,
    queue_name="default",
    now=None,
    stale_after_seconds=60,
):
    """Evaluate whether a scan record's background job is healthy."""
    now = now or timezone.now()
    core_status = (core_status or "").lower() or None
    queue_status = (queue_status or "").lower() or None
    queue_name = queue_name or "default"
    core_error = (core_error or "").strip()

    if record_status not in ACTIVE_SCAN_STATUSES:
        return ScanJobHealth(
            core_status=core_status,
            queue_status=queue_status,
            queue_name=queue_name,
            should_mark_failed=False,
            error_message="",
            detail_message="This scan record is already in a terminal state.",
        )

    if core_status in FAILED_CORE_JOB_STATUSES:
        error_message = core_error or f"Background scan job {job_id} failed."
        return ScanJobHealth(
            core_status=core_status,
            queue_status=queue_status,
            queue_name=queue_name,
            should_mark_failed=True,
            error_message=error_message,
            detail_message=error_message,
        )

    if core_status == "completed":
        error_message = (
            core_error
            or f"Background scan job {job_id} completed without finalizing the scan record."
        )
        return ScanJobHealth(
            core_status=core_status,
            queue_status=queue_status,
            queue_name=queue_name,
            should_mark_failed=True,
            error_message=error_message,
            detail_message=error_message,
        )

    if queue_status == "started":
        return ScanJobHealth(
            core_status=core_status,
            queue_status=queue_status,
            queue_name=queue_name,
            should_mark_failed=False,
            error_message="",
            detail_message="The worker is actively processing this scan.",
        )

    if queue_status in {"queued", "scheduled", "deferred"}:
        return ScanJobHealth(
            core_status=core_status,
            queue_status=queue_status,
            queue_name=queue_name,
            should_mark_failed=False,
            error_message="",
            detail_message=f"This scan is waiting in the {queue_name!r} queue.",
        )

    stale_cutoff = now - timedelta(seconds=int(stale_after_seconds))
    if queue_status == "missing" and core_status in ACTIVE_CORE_JOB_STATUSES:
        if started_at and started_at > stale_cutoff:
            return ScanJobHealth(
                core_status=core_status,
                queue_status=queue_status,
                queue_name=queue_name,
                should_mark_failed=False,
                error_message="",
                detail_message="NetBox has created the job record, but the worker has not yet claimed it.",
            )

        error_message = build_orphaned_job_error(job_id, queue_name)
        return ScanJobHealth(
            core_status=core_status,
            queue_status=queue_status,
            queue_name=queue_name,
            should_mark_failed=True,
            error_message=error_message,
            detail_message=error_message,
        )

    return ScanJobHealth(
        core_status=core_status,
        queue_status=queue_status,
        queue_name=queue_name,
        should_mark_failed=False,
        error_message="",
        detail_message="No queue/runtime issue was detected for this scan.",
    )


def inspect_queue_job(job_id, queue_name):
    """Return the current RQ status for the given job UUID."""
    queue = django_rq.get_queue(queue_name or "default")
    try:
        job = RQJob.fetch(str(job_id), connection=queue.connection)
    except NoSuchJobError:
        return "missing"
    return (job.get_status(refresh=False) or "").lower() or None


def reconcile_scan_record_job(scan_record, stale_after_seconds=60):
    """Synchronize a scan record with NetBox core job and RQ state."""
    queue_name = "default"
    core_job = None
    core_status = None
    core_error = ""
    queue_status = None

    if scan_record.job_id:
        core_job = CoreJob.objects.filter(job_id=scan_record.job_id).first()
        if core_job:
            queue_name = core_job.queue_name or queue_name
            core_status = core_job.status
            core_error = core_job.error or ""
        queue_status = inspect_queue_job(scan_record.job_id, queue_name)

    health = evaluate_scan_job_health(
        record_status=scan_record.status,
        job_id=scan_record.job_id,
        started_at=scan_record.started_at,
        core_status=core_status,
        core_error=core_error,
        queue_status=queue_status,
        queue_name=queue_name,
        stale_after_seconds=stale_after_seconds,
    )

    if not health.should_mark_failed:
        return health

    now = timezone.now()
    record_fields = []
    if scan_record.status != NetworkScanStatusChoices.FAILED:
        scan_record.status = NetworkScanStatusChoices.FAILED
        record_fields.append("status")
    if scan_record.finished_at is None:
        scan_record.finished_at = now
        record_fields.append("finished_at")
    if scan_record.error != health.error_message:
        scan_record.error = health.error_message
        record_fields.append("error")
    if record_fields:
        scan_record.save(update_fields=record_fields + ["last_updated"])

    if core_job and core_job.status in ACTIVE_CORE_JOB_STATUSES:
        core_job.status = NetworkScanStatusChoices.FAILED
        core_job.completed = now
        core_job.error = health.error_message
        core_job.save(update_fields=["status", "completed", "error"])

    return health
