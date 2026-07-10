"""Tests for subnet/range discovery helpers."""

from django.test import SimpleTestCase
from unittest.mock import patch

from netmapper.network_discovery import (
    build_identity_note,
    build_scan_plan,
    candidate_to_summary,
    expand_target_spec_addresses,
    estimate_target_host_count,
    infer_device_role,
    infer_discovery_mode,
    merge_identity_note,
    normalize_snmp_communities,
    run_snmp_identity_probe,
    parse_nmap_xml_hosts,
    parse_snmpget_output,
    parse_target_specs,
    scan_host_candidates,
    NmapHostResult,
    ScannedHostCandidate,
    SnmpHostMetadata,
)


class NetworkDiscoveryHelperTest(SimpleTestCase):
    """Validate helper logic without requiring live network tools."""

    def test_parse_target_specs(self):
        """CIDRs, addresses, and ranges should normalize cleanly."""
        valid_targets, invalid_targets = parse_target_specs(
            "192.0.2.1 192.0.2.0/30 192.0.2.10-192.0.2.12 192.0.2.20-22 invalid"
        )
        self.assertEqual(
            valid_targets,
            [
                "192.0.2.1",
                "192.0.2.0/30",
                "192.0.2.10-192.0.2.12",
                "192.0.2.20-192.0.2.22",
            ],
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

    def test_expand_target_spec_addresses(self):
        """Target expansion should preserve host addresses in order."""
        addresses = expand_target_spec_addresses(
            ["192.0.2.1", "192.0.2.10-192.0.2.12", "192.0.2.20-22", "192.0.2.4/31"]
        )
        self.assertEqual(
            addresses,
            [
                "192.0.2.1",
                "192.0.2.10",
                "192.0.2.11",
                "192.0.2.12",
                "192.0.2.20",
                "192.0.2.21",
                "192.0.2.22",
                "192.0.2.4",
                "192.0.2.5",
            ],
        )

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

    def test_normalize_snmp_communities_adds_public_fallback(self):
        """A custom SNMP community should fall back to public once."""
        communities = normalize_snmp_communities(
            "kavanoz06",
            fallback_communities=["public"],
        )
        self.assertEqual(communities, ["kavanoz06", "public"])

    def test_normalize_snmp_communities_appends_fallback_uniquely(self):
        """Community parsing should preserve order and avoid duplicates."""
        communities = normalize_snmp_communities(
            "kavanoz06, public",
            fallback_communities=["public"],
        )
        self.assertEqual(communities, ["kavanoz06", "public"])

    @patch("netmapper.network_discovery.subprocess.run")
    def test_run_snmp_identity_probe_handles_multiline_sysdescr(self, mock_run):
        """SNMP identity probing should preserve multiline sysDescr output."""
        mock_run.side_effect = [
            type("Result", (), {"returncode": 0, "stdout": "edge-sw1\n", "stderr": ""})(),
            type(
                "Result",
                (),
                {
                    "returncode": 0,
                    "stdout": (
                        "Cisco IOS Software, C2960 Software (C2960-LANBASEK9-M), Version 12.2(55)SE1\n"
                        "Technical Support: http://www.cisco.com/techsupport\n"
                        "Compiled Thu 02-Dec-10 08:16 by prod_rel_team\n"
                    ),
                    "stderr": "",
                },
            )(),
            type(
                "Result",
                (),
                {
                    "returncode": 0,
                    "stdout": "1.3.6.1.4.1.9.1.516\n",
                    "stderr": "",
                },
            )(),
        ]

        metadata = run_snmp_identity_probe(
            address="192.0.2.10",
            community="public",
            executable="snmpget",
        )

        self.assertEqual(metadata.sys_name, "edge-sw1")
        self.assertIn("Cisco IOS Software", metadata.sys_descr)
        self.assertIn("Technical Support", metadata.sys_descr)
        self.assertEqual(metadata.sys_object_id, "1.3.6.1.4.1.9.1.516")
        self.assertIsNone(metadata.error)

    @patch("netmapper.network_discovery.subprocess.run")
    def test_run_snmp_identity_probe_retries_next_community(self, mock_run):
        """SNMP identity probing should fall through to the next community."""
        mock_run.side_effect = [
            type("Result", (), {"returncode": 1, "stdout": "", "stderr": "Timeout"})(),
            type("Result", (), {"returncode": 1, "stdout": "", "stderr": "Timeout"})(),
            type("Result", (), {"returncode": 1, "stdout": "", "stderr": "Timeout"})(),
            type("Result", (), {"returncode": 0, "stdout": "yealink-lobby\n", "stderr": ""})(),
            type(
                "Result",
                (),
                {
                    "returncode": 0,
                    "stdout": "Yealink SIP-T54W IP Phone\n",
                    "stderr": "",
                },
            )(),
            type(
                "Result",
                (),
                {
                    "returncode": 0,
                    "stdout": "1.3.6.1.4.1.1916.1.170\n",
                    "stderr": "",
                },
            )(),
        ]

        metadata = run_snmp_identity_probe(
            address="192.0.2.55",
            community=["kavanoz06", "public"],
            executable="snmpget",
        )

        self.assertEqual(metadata.sys_name, "yealink-lobby")
        self.assertEqual(metadata.sys_descr, "Yealink SIP-T54W IP Phone")
        self.assertEqual(metadata.sys_object_id, "1.3.6.1.4.1.1916.1.170")
        self.assertIsNone(metadata.error)

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
            inferred_role="switch",
            role_confidence="medium",
            role_reason="Matched identity marker 'cisco ios'",
        )
        self.assertIn("Address: 192.0.2.10", note)
        self.assertIn("Nmap hostname: edge-sw1", note)
        self.assertIn("SNMP sysName: edge-sw1", note)
        self.assertIn("Suggested role: switch (medium confidence)", note)
        merged = merge_identity_note("Existing comments", note)
        self.assertIn("Existing comments", merged)
        self.assertIn("Network scan identity", merged)

    def test_infer_device_role(self):
        """Identity markers should produce stable role suggestions."""
        role, confidence, reason = infer_device_role(
            sys_descr="Cisco Adaptive Security Appliance Version 9.18",
            hostname="fw-edge-1",
        )
        self.assertEqual(role, "firewall")
        self.assertEqual(confidence, "high")
        self.assertIn("adaptive security appliance", reason)
        role, confidence, reason = infer_device_role(
            sys_descr="Cisco IOS Software, C9300",
            hostname="core-sw1",
        )
        self.assertEqual(role, "switch")
        self.assertEqual(confidence, "medium")
        self.assertTrue("c9300" in reason or "switch" in reason)
        role, confidence, reason = infer_device_role(
            sys_descr="Yealink SIP-T54W IP Phone",
            hostname="lobby-phone",
            vendor="Yealink",
        )
        self.assertEqual(role, "phone")
        self.assertEqual(confidence, "high")
        self.assertIn("yealink", reason.lower())

    def test_candidate_to_summary_includes_role_metadata(self):
        """Candidate summaries should expose role inference details to the UI."""
        candidate = ScannedHostCandidate(
            host=NmapHostResult(address="192.0.2.10", hostname="fw-edge-1"),
            selected_mode="netmiko_cisco_ios",
            inferred_mode="netmiko_cisco_ios",
            snmp_metadata=SnmpHostMetadata(
                address="192.0.2.10",
                sys_name="fw-edge-1",
                sys_descr="Cisco Adaptive Security Appliance",
                sys_object_id="1.3.6.1.4.1.9.1.669",
            ),
            identity_note="identity",
            inferred_role="firewall",
            role_confidence="high",
            role_reason="Matched identity marker 'firewall'",
        )
        summary = candidate_to_summary(candidate)
        self.assertEqual(summary["inferred_role"], "firewall")
        self.assertEqual(summary["role_confidence"], "high")
        self.assertIn("Matched identity marker", summary["role_reason"])

    @patch("netmapper.network_discovery.run_snmp_identity_probe")
    @patch("netmapper.network_discovery.run_nmap_ping_scan")
    def test_scan_host_candidates_probes_snmp_for_hosts_missed_by_nmap(
        self, mock_nmap_scan, mock_snmp_probe
    ):
        """SNMP fallback should include hosts that ping discovery misses."""
        mock_nmap_scan.return_value = [
            NmapHostResult(address="192.0.2.15", hostname="seen-by-nmap")
        ]

        def snmp_side_effect(address, **kwargs):
            suffix = address.rsplit(".", maxsplit=1)[-1]
            return SnmpHostMetadata(
                address=address,
                sys_name=f"sw-{suffix}",
                sys_descr="Cisco IOS Software, C2960 Software",
                sys_object_id=f"1.3.6.1.4.1.9.1.5{suffix}",
            )

        mock_snmp_probe.side_effect = snmp_side_effect

        candidates = scan_host_candidates(
            ["192.0.2.10-15"],
            default_mode="linux",
            snmp_community="public",
            host_timeout=10,
            snmp_timeout=2,
        )

        self.assertEqual([candidate.host.address for candidate in candidates], [
            "192.0.2.15",
            "192.0.2.10",
            "192.0.2.11",
            "192.0.2.12",
            "192.0.2.13",
            "192.0.2.14",
        ])
        self.assertTrue(
            all(candidate.selected_mode == "netmiko_cisco_ios" for candidate in candidates)
        )
        self.assertTrue(
            all(candidate.snmp_metadata and candidate.snmp_metadata.sys_name for candidate in candidates)
        )
        self.assertTrue(all(candidate.inferred_role == "switch" for candidate in candidates))

    @patch("netmapper.network_discovery.run_snmp_identity_probe")
    @patch("netmapper.network_discovery.run_nmap_ping_scan")
    def test_scan_host_candidates_uses_public_as_fallback_community(
        self, mock_nmap_scan, mock_snmp_probe
    ):
        """Subnet scans should append public after the user-supplied community."""
        mock_nmap_scan.return_value = [NmapHostResult(address="192.0.2.131")]
        mock_snmp_probe.return_value = SnmpHostMetadata(
            address="192.0.2.131",
            sys_name="yealink-lobby",
            sys_descr="Yealink SIP-T54W IP Phone",
            sys_object_id="1.3.6.1.4.1.1916.1.170",
        )

        candidates = scan_host_candidates(
            ["192.0.2.131-140"],
            default_mode="netmiko_cisco_ios",
            snmp_community="kavanoz06",
            host_timeout=10,
            snmp_timeout=2,
        )

        self.assertEqual(len(candidates), 1)
        _, kwargs = mock_snmp_probe.call_args
        self.assertEqual(kwargs["community"], ["kavanoz06", "public"])
