"""Tests for generic scan-to-device seeding."""

from django.test import TestCase

from dcim.models import DeviceRole, DeviceType, Manufacturer, Site

from netmapper.models import Credential, Discoverable
from netmapper.network_discovery import NmapHostResult, ScannedHostCandidate, SnmpHostMetadata
from netmapper.scan_ingestion import (
    candidate_requires_generic_seed,
    seed_device_from_scan_candidate,
)


class ScanIngestionTests(TestCase):
    """Validate generic scan seeding for unsupported but identified devices."""

    def setUp(self):
        self.site = Site.objects.create(name="Test Site", slug="test-site")
        self.credential = Credential.objects.create(
            name="scan-credential",
            username="user",
            password="",
        )
        self.discoverable = Discoverable.objects.create(
            address="192.0.2.55",
            credential=self.credential,
            mode="netmiko_cisco_ios",
            site=self.site,
            discoverable=True,
        )

    def test_candidate_requires_generic_seed_for_unmapped_snmp_identity(self):
        """SNMP-identified hosts without a discovery driver should use generic seeding."""
        candidate = ScannedHostCandidate(
            host=NmapHostResult(address="192.0.2.55", vendor="Yealink"),
            selected_mode="netmiko_cisco_ios",
            inferred_mode=None,
            snmp_metadata=SnmpHostMetadata(
                address="192.0.2.55",
                sys_name="yealink-lobby",
                sys_descr="Yealink SIP-T54W IP Phone",
                sys_object_id="1.3.6.1.4.1.1916.1.170",
            ),
        )
        self.assertTrue(candidate_requires_generic_seed(candidate))

    def test_seed_device_from_scan_candidate_creates_generic_device(self):
        """A Yealink-like endpoint should become a linked NetBox device with management IP."""
        candidate = ScannedHostCandidate(
            host=NmapHostResult(
                address="192.0.2.55",
                hostname="yealink-lobby",
                mac_address="AA:BB:CC:DD:EE:55",
                vendor="Yealink",
            ),
            selected_mode="netmiko_cisco_ios",
            inferred_mode=None,
            snmp_metadata=SnmpHostMetadata(
                address="192.0.2.55",
                sys_name="yealink-lobby",
                sys_descr="Yealink SIP-T54W IP Phone",
                sys_object_id="1.3.6.1.4.1.1916.1.170",
            ),
            inferred_role="phone",
        )

        device_o, created = seed_device_from_scan_candidate(
            self.discoverable,
            candidate,
        )
        self.discoverable.refresh_from_db()
        device_o.refresh_from_db()

        self.assertTrue(created)
        self.assertEqual(self.discoverable.device_id, device_o.id)
        self.assertEqual(device_o.name, "YEALINK-LOBBY")
        self.assertEqual(device_o.primary_ip4.address.ip.compressed, "192.0.2.55")
        self.assertEqual(device_o.role.name, "Phone")

        manufacturer_o = Manufacturer.objects.get(name="Yealink")
        device_type_o = DeviceType.objects.get(
            manufacturer=manufacturer_o,
            model="SIP-T54W",
        )
        self.assertEqual(device_o.device_type_id, device_type_o.id)
        self.assertEqual(DeviceRole.objects.get(name="Phone").slug, "phone")
