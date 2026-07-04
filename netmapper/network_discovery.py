"""Helpers for subnet/range discovery via Nmap and SNMP."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
import subprocess
from typing import Iterable

import xmltodict

TARGET_SPLIT_RE = re.compile(r"[\s,;]+")
SNMP_EMPTY_MARKERS = (
    "No Such Object",
    "No Such Instance",
    "No more variables",
    "Timeout:",
)


@dataclass(frozen=True)
class NmapHostResult:
    """Responsive host returned by an Nmap scan."""

    address: str
    hostname: str | None = None
    mac_address: str | None = None
    vendor: str | None = None
    status: str = "up"


@dataclass(frozen=True)
class SnmpHostMetadata:
    """Minimal SNMP identity collected for a host."""

    address: str
    sys_name: str | None = None
    sys_descr: str | None = None
    sys_object_id: str | None = None
    error: str | None = None


def _ensure_list(value):
    """Always return a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def split_target_input(raw_targets):
    """Split a free-form target string into tokens."""
    if not raw_targets:
        return []
    return [token.strip() for token in TARGET_SPLIT_RE.split(raw_targets) if token.strip()]


def normalize_target_spec(target):
    """Validate and normalize an IP/CIDR/range target."""
    if "-" in target and "/" not in target:
        start, end = [item.strip() for item in target.split("-", maxsplit=1)]
        start_ip = ipaddress.ip_address(start)
        end_ip = ipaddress.ip_address(end)
        if start_ip.version != end_ip.version:
            raise ValueError(f"IP range {target} mixes address families")
        if int(start_ip) > int(end_ip):
            raise ValueError(f"IP range {target} has start after end")
        return f"{start_ip.compressed}-{end_ip.compressed}"

    if "/" in target:
        network = ipaddress.ip_network(target, strict=False)
        return str(network)

    address = ipaddress.ip_address(target)
    return address.compressed


def parse_target_specs(raw_targets):
    """Parse targets, returning normalized specs plus invalid tokens."""
    valid_targets = []
    invalid_targets = []
    for token in split_target_input(raw_targets):
        try:
            valid_targets.append(normalize_target_spec(token))
        except ValueError:
            invalid_targets.append(token)
    return list(dict.fromkeys(valid_targets)), invalid_targets


def estimate_target_host_count(target_specs: Iterable[str]) -> int:
    """Estimate how many addresses a scan could touch."""
    total = 0
    for target in target_specs:
        if "-" in target and "/" not in target:
            start, end = target.split("-", maxsplit=1)
            total += int(ipaddress.ip_address(end)) - int(ipaddress.ip_address(start)) + 1
        elif "/" in target:
            total += ipaddress.ip_network(target, strict=False).num_addresses
        else:
            total += 1
    return total


def parse_nmap_xml_hosts(xml_output):
    """Parse Nmap XML output and return responsive hosts."""
    parsed = xmltodict.parse(xml_output)
    hosts = []
    for host in _ensure_list(parsed.get("nmaprun", {}).get("host")):
        if host.get("status", {}).get("@state") != "up":
            continue

        ipv4_or_v6 = None
        mac_address = None
        vendor = None
        for address in _ensure_list(host.get("address")):
            addr_type = address.get("@addrtype")
            if addr_type in ("ipv4", "ipv6") and not ipv4_or_v6:
                ipv4_or_v6 = address.get("@addr")
            elif addr_type == "mac":
                mac_address = address.get("@addr")
                vendor = address.get("@vendor")

        hostname = None
        hostnames = host.get("hostnames") or {}
        hostname_entries = _ensure_list(hostnames.get("hostname"))
        if hostname_entries:
            hostname = hostname_entries[0].get("@name")

        if ipv4_or_v6:
            hosts.append(
                NmapHostResult(
                    address=ipv4_or_v6,
                    hostname=hostname,
                    mac_address=mac_address,
                    vendor=vendor,
                    status="up",
                )
            )

    return hosts


def run_nmap_ping_scan(target_specs, host_timeout=30, executable="nmap"):
    """Run an Nmap ping scan and return responsive hosts."""
    if not target_specs:
        return []

    command = [
        executable,
        "-sn",
        "-n",
        "--host-timeout",
        f"{int(host_timeout)}s",
        "-oX",
        "-",
        *target_specs,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Nmap executable '{executable}' was not found in the runtime container"
        ) from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(stderr or "Nmap scan failed")

    return parse_nmap_xml_hosts(result.stdout)


def _normalize_snmp_value(value):
    """Convert raw snmpget output to a clean value."""
    if value is None:
        return None
    cleaned = value.strip().strip('"')
    if not cleaned:
        return None
    for marker in SNMP_EMPTY_MARKERS:
        if cleaned.startswith(marker):
            return None
    return cleaned


def parse_snmpget_output(address, output):
    """Parse three-line snmpget output into structured metadata."""
    values = [_normalize_snmp_value(line) for line in output.splitlines()]
    while len(values) < 3:
        values.append(None)
    return SnmpHostMetadata(
        address=address,
        sys_name=values[0],
        sys_descr=values[1],
        sys_object_id=values[2],
    )


def run_snmp_identity_probe(
    address,
    community,
    timeout=2,
    retries=0,
    executable="snmpget",
):
    """Query basic SNMP identity fields for a host."""
    command = [
        executable,
        "-v2c",
        "-c",
        community,
        "-t",
        str(timeout),
        "-r",
        str(retries),
        "-Oqv",
        address,
        "1.3.6.1.2.1.1.5.0",  # sysName.0
        "1.3.6.1.2.1.1.1.0",  # sysDescr.0
        "1.3.6.1.2.1.1.2.0",  # sysObjectID.0
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"SNMP executable '{executable}' was not found in the runtime container"
        ) from exc

    if result.returncode != 0:
        error = (result.stderr or result.stdout or "").strip() or "SNMP probe failed"
        return SnmpHostMetadata(address=address, error=error)

    return parse_snmpget_output(address, result.stdout)


def infer_discovery_mode(
    sys_descr=None,
    sys_object_id=None,
    hostname=None,
    vendor=None,
):
    """Infer the best discovery mode from lightweight identity data."""
    fingerprint = " ".join(
        value
        for value in [sys_descr, sys_object_id, hostname, vendor]
        if value
    ).lower()

    if not fingerprint:
        return None
    if "palo alto" in fingerprint or "pan-os" in fingerprint or "panos" in fingerprint:
        return "xml_panw_ngfw"
    if "ios xr" in fingerprint or "cisco xr" in fingerprint:
        return "netmiko_cisco_xr"
    if "nx-os" in fingerprint or "nxos" in fingerprint or "nexus" in fingerprint:
        return "netmiko_cisco_nxos"
    if "cisco ios" in fingerprint or "internetwork operating system" in fingerprint:
        return "netmiko_cisco_ios"
    if "arubaos-cx" in fingerprint or "aruba cx" in fingerprint or "aoscx" in fingerprint:
        return "netmiko_aruba_aoscx"
    if "comware" in fingerprint:
        return "netmiko_hp_comware"
    if "procurve" in fingerprint or "arubaos-switch" in fingerprint:
        return "netmiko_hp_procurve"
    if "huawei" in fingerprint or "vrp" in fingerprint:
        return "netmiko_huawei_vrp"
    if "allied telesis" in fingerprint or "alliedware plus" in fingerprint or "aw+" in fingerprint:
        return "netmiko_allied_telesis_awplus"
    if "linux" in fingerprint or "unix" in fingerprint:
        return "netmiko_linux"
    if "cisco" in fingerprint:
        return "netmiko_cisco_ios"
    return None
