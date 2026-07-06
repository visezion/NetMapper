"""Tests for scan job health reconciliation helpers."""

from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from netmapper.job_tracking import evaluate_scan_job_health, normalize_job_uuid
from netmapper.models import NetworkScanStatusChoices


class ScanJobHealthTest(SimpleTestCase):
    """Validate stale-job detection and failure surfacing."""

    def test_marks_orphaned_running_job_as_failed(self):
        """A missing queue job should fail a long-running active scan."""
        health = evaluate_scan_job_health(
            record_status=NetworkScanStatusChoices.RUNNING,
            job_id="1234",
            started_at=timezone.now() - timedelta(minutes=5),
            core_status="running",
            queue_status="missing",
            queue_name="default",
        )

        self.assertTrue(health.should_mark_failed)
        self.assertIn("no longer present", health.error_message)
        self.assertIn("restarted", health.error_message)

    def test_surfaces_core_job_failure_message(self):
        """A failed NetBox core job should feed its error into the scan record."""
        health = evaluate_scan_job_health(
            record_status=NetworkScanStatusChoices.RUNNING,
            job_id="1234",
            started_at=timezone.now(),
            core_status="failed",
            core_error="SNMP probe timed out",
            queue_status="missing",
            queue_name="default",
        )

        self.assertTrue(health.should_mark_failed)
        self.assertEqual(health.error_message, "SNMP probe timed out")

    def test_keeps_started_job_running(self):
        """An actively started worker job should not be marked failed."""
        health = evaluate_scan_job_health(
            record_status=NetworkScanStatusChoices.RUNNING,
            job_id="1234",
            started_at=timezone.now(),
            core_status="running",
            queue_status="started",
            queue_name="default",
        )

        self.assertFalse(health.should_mark_failed)
        self.assertIn("actively processing", health.detail_message)

    def test_marks_old_record_without_job_id_as_failed(self):
        """A long-lived active record without a job ID should be surfaced as failed."""
        health = evaluate_scan_job_health(
            record_status=NetworkScanStatusChoices.QUEUED,
            job_id="",
            started_at=timezone.now() - timedelta(minutes=5),
            queue_name="default",
        )

        self.assertTrue(health.should_mark_failed)
        self.assertIn("does not have a background job ID", health.error_message)

    def test_marks_invalid_legacy_job_id_as_failed(self):
        """A malformed non-UUID job ID should not crash reconciliation."""
        health = evaluate_scan_job_health(
            record_status=NetworkScanStatusChoices.RUNNING,
            job_id="3",
            started_at=timezone.now() - timedelta(minutes=5),
            queue_name="default",
        )

        self.assertTrue(health.should_mark_failed)
        self.assertIn("invalid background job ID", health.error_message)

    def test_normalize_job_uuid_rejects_legacy_numeric_ids(self):
        """Legacy numeric job IDs should be treated as invalid UUIDs."""
        self.assertIsNone(normalize_job_uuid("3"))
