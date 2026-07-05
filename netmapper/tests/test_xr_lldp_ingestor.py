"""Regression tests for the Cisco XR LLDP ingestor."""

from types import SimpleNamespace

from django.test import TestCase

from dcim.models import Interface, Site

from netmapper.ingestors.netmiko_cisco_xr_show_lldp_neighbors import ingest
from netmapper.models import Credential, Discoverable
from netmapper.schemas import device as device_schema


class _FakeLog(SimpleNamespace):
    """Minimal log stub accepted by the ingestor."""

    def save(self):
        """Match the DiscoveryLog interface used by ingestors."""


class CiscoXrLldpIngestorTest(TestCase):
    """Verify XR LLDP neighbor ingestion with current parser keys."""

    def setUp(self):
        self.site = Site.objects.create(name="Test Site", slug="test-site")
        self.device = device_schema.create(name="XR01", site_id=self.site.id)
        self.credential = Credential.objects.create(
            name="test-credential",
            username="tester",
            password="secret",
        )
        self.discoverable = Discoverable.objects.create(
            address="192.0.2.10",
            device=self.device,
            credential=self.credential,
            mode="netmiko_cisco_xr",
            site=self.site,
        )

    def test_ingest_uses_neighbor_name_field(self):
        """Current ntc-templates expose neighbor_name for XR LLDP entries."""
        log = _FakeLog(
            discoverable=self.discoverable,
            parsed_output=[
                {
                    "local_interface": "Gi0/0/0/2",
                    "neighbor_name": "XR03",
                    "neighbor_interface": "Gi0/0/0/2",
                },
                {
                    "local_interface": "Gi0/0/0/3",
                    "neighbor_name": "XR03",
                    "neighbor_interface": "Gi0/0/0/3",
                },
            ],
            ingested=False,
        )

        ingest(log)

        self.assertTrue(log.ingested)
        self.assertEqual(
            list(
                Interface.objects.filter(device__name="XR03")
                .order_by("label")
                .values_list("label", flat=True)
            ),
            ["gi0/0/0/2", "gi0/0/0/3"],
        )
