"""Tests for subnet/range discovery helpers."""

from django.test import SimpleTestCase

from netmapper.network_discovery import (
    build_identity_note,
    build_scan_plan,
    estimate_target_host_count,
    infer_discovery_mode,
    merge_identity_note,
    parse_nmap_xml_hosts,
    parse_snmpget_output,
    parse_target_specs,
    NmapHostResult,
    SnmpHostMetadata,
)


class NetworkDiscoveryHelperTest(SimpleTestCase):
    """Validate helper logic without requiring live network tools."""

    def test_parse_target_specs(self):
        """CIDRs, addresses, and ranges should normalize cleanly."""
        valid_targets, invalid_targets = parse_target_specs(
            "192.0.2.1 192.0.2.0/30 192.0.2.10-192.0.2.12 invalid"
        )
        self.assertEqual(
            valid_targets,
            ["192.0.2.1", "192.0.2.0/30", "192.0.2.10-192.0.2.12"],
        )
        self.assertEqual(invalid_targets, ["invalid"])

    def test_estimate_target_host_count(self):
        """Target estimation should include networks, ranges, and single IPs."""
        total = estimate_target_host_count(
            ["192.0.2.1", "192.0.2.0/30", "192.0.2.10-192.0.2.12"]
        )
        self.assertEqual(total, 8)

    def test_build_scan_plan(self):
        """The scan plan should include normalized and invalid target details."""
        plan = build_scan_plan(
            "192.0.2.1\n192.0.2.0/30 invalid",
            max_hosts=3,
        )
        self.assertEqual(plan.normalized_targets, ["192.0.2.1", "192.0.2.0/30"])
        self.assertEqual(plan.invalid_targets, ["invalid"])
        self.assertEqual(plan.estimated_host_count, 5)
        self.assertTrue(plan.exceeds_max_hosts)

    def test_parse_nmap_xml_hosts(self):
        """Nmap XML should produce responsive host records."""
        xml_output = """
        <nmaprun>
          <host>
            <status state="up" />
            <address addr="192.0.2.10" addrtype="ipv4" />
            <address addr="AA:BB:CC:DD:EE:FF" addrtype="mac" vendor="Cisco" />
            <hostnames>
              <hostname name="core-sw1" type="user" />
            </hostnames>
          </host>
          <host>
            <status state="down" />
            <address addr="192.0.2.11" addrtype="ipv4" />
          </host>
        </nmaprun>
        """
        hosts = parse_nmap_xml_hosts(xml_output)
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].address, "192.0.2.10")
        self.assertEqual(hosts[0].hostname, "core-sw1")
        self.assertEqual(hosts[0].vendor, "Cisco")

    def test_parse_snmpget_output(self):
        """snmpget output should map to identity fields in order."""
        metadata = parse_snmpget_output(
            "192.0.2.10",
            "core-sw1\nCisco IOS Software, C9300\n1.3.6.1.4.1.9.1.1745\n",
        )
        self.assertEqual(metadata.sys_name, "core-sw1")
        self.assertEqual(metadata.sys_descr, "Cisco IOS Software, C9300")
        self.assertEqual(metadata.sys_object_id, "1.3.6.1.4.1.9.1.1745")

    def test_infer_discovery_mode(self):
        """SNMP fingerprints should map to known discovery modes."""
        self.assertEqual(
            infer_discovery_mode(sys_descr="Cisco NX-OS(tm) n9000 software"),
            "netmiko_cisco_nxos",
        )
        self.assertEqual(
            infer_discovery_mode(sys_descr="Huawei Versatile Routing Platform Software"),
            "netmiko_huawei_vrp",
        )
        self.assertEqual(
            infer_discovery_mode(sys_descr="PAN-OS 11.1.0"),
            "xml_panw_ngfw",
        )
        self.assertEqual(
            infer_discovery_mode(
                sys_descr="Cisco IOS XE Software, Version 17.09.04a",
                vendor="Cisco",
            ),
            "netmiko_cisco_ios",
        )
        self.assertEqual(
            infer_discovery_mode(
                sys_descr="ArubaOS-CX Virtual.10.13",
                hostname="leaf-a",
            ),
            "netmiko_aruba_aoscx",
        )

    def test_build_identity_note_and_merge(self):
        """Identity notes should include observed details and append cleanly."""
        host = NmapHostResult(
            address="192.0.2.10",
            hostname="edge-sw1",
            mac_address="AA:BB:CC:DD:EE:FF",
            vendor="Cisco",
        )
        snmp = SnmpHostMetadata(
            address="192.0.2.10",
            sys_name="edge-sw1",
            sys_descr="Cisco IOS XE Software",
            sys_object_id="1.3.6.1.4.1.9.1.1208",
        )
        note = build_identity_note(
            host,
            snmp_metadata=snmp,
            selected_mode="netmiko_cisco_ios",
            inferred_mode="netmiko_cisco_ios",
        )
        self.assertIn("Address: 192.0.2.10", note)
        self.assertIn("Nmap hostname: edge-sw1", note)
        self.assertIn("SNMP sysName: edge-sw1", note)
        merged = merge_identity_note("Existing comments", note)
        self.assertIn("Existing comments", merged)
        self.assertIn("Network scan identity", merged)
