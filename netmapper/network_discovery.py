"""Helpers for subnet/range discovery via Nmap and SNMP."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
import subprocess
from datetime import datetime, UTC
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


@dataclass(frozen=True)
class ScanPlanResult:
    """Target parsing and sizing result."""

    raw_targets: str
    normalized_targets: list[str]
    invalid_targets: list[str]
    estimated_host_count: int
    max_hosts: int

    @property
    def exceeds_max_hosts(self):
        """Return True when the requested scan exceeds the configured cap."""
        return self.estimated_host_count > self.max_hosts


@dataclass(frozen=True)
class ScannedHostCandidate:
    """Host result enriched with SNMP inference and note text."""

    host: NmapHostResult
    selected_mode: str
    inferred_mode: str | None = None
    snmp_metadata: SnmpHostMetadata | None = None
    identity_note: str | None = None

    @property
    def snmp_failed(self):
        """Return True when SNMP was attempted but failed."""
        return bool(self.snmp_metadata and self.snmp_metadata.error)


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


def _normalize_range_endpoint(start, end):
    """Expand shorthand IPv4 range endpoints such as 192.0.2.10-15."""
    if "." in end or ":" in end:
        return end

    start_ip = ipaddress.ip_address(start)
    if start_ip.version != 4 or not end.isdigit():
        return end

    end_octet = int(end)
    if not 0 <= end_octet <= 255:
        raise ValueError(f"IP range {start}-{end} has invalid IPv4 end octet")

    start_octets = start_ip.compressed.split(".")
    return ".".join([*start_octets[:3], str(end_octet)])


def normalize_target_spec(target):
    """Validate and normalize an IP/CIDR/range target."""
    if "-" in target and "/" not in target:
        start, end = [item.strip() for item in target.split("-", maxsplit=1)]
        end = _normalize_range_endpoint(start, end)
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


def build_scan_plan(raw_targets, max_hosts):
    """Return a full scan plan including normalized targets and safety checks."""
    normalized_targets, invalid_targets = parse_target_specs(raw_targets)
    estimated_host_count = estimate_target_host_count(normalized_targets)
    return ScanPlanResult(
        raw_targets=raw_targets or "",
        normalized_targets=normalized_targets,
        invalid_targets=invalid_targets,
        estimated_host_count=estimated_host_count,
        max_hosts=max_hosts,
    )


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


def expand_target_spec_addresses(target_specs: Iterable[str]) -> list[str]:
    """Expand target specs into individual host addresses."""
    expanded = []
    for target in target_specs:
        target = normalize_target_spec(str(target).strip())
        if "-" in target and "/" not in target:
            start, end = target.split("-", maxsplit=1)
            start_ip = ipaddress.ip_address(start)
            end_ip = ipaddress.ip_address(end)
            current = int(start_ip)
            while current <= int(end_ip):
                expanded.append(ipaddress.ip_address(current).compressed)
                current += 1
            continue

        if "/" in target:
            network = ipaddress.ip_network(target, strict=False)
            expanded.extend(address.compressed for address in network.hosts())
            if network.num_addresses == 1:
                expanded.append(network.network_address.compressed)
            continue

        expanded.append(ipaddress.ip_address(target).compressed)

    return list(dict.fromkeys(expanded))


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


def _run_snmpget_value(
    address,
    community,
    oid,
    port=161,
    version="v2c",
    timeout=2,
    retries=0,
    executable="snmpget",
):
    """Query a single SNMP value and return the normalized response."""
    target = address
    if port and int(port) != 161:
        if ":" in address and not address.startswith("["):
            target = f"udp6:[{address}]:{int(port)}"
        else:
            target = f"udp:{address}:{int(port)}"
    command = [
        executable,
        f"-{version}",
        "-c",
        community,
        "-t",
        str(timeout),
        "-r",
        str(retries),
        "-Oqv",
        target,
        oid,
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
        return None, error

    return _normalize_snmp_value(result.stdout), None


def snmp_metadata_has_identity(metadata):
    """Return True when SNMP metadata contains any useful identity field."""
    return bool(
        metadata
        and (
            metadata.sys_name
            or metadata.sys_descr
            or metadata.sys_object_id
        )
    )


def run_snmp_identity_probe(
    address,
    community,
    port=161,
    version="v2c",
    timeout=2,
    retries=0,
    executable="snmpget",
):
    """Query basic SNMP identity fields for a host."""
    oid_map = {
        "sys_name": "1.3.6.1.2.1.1.5.0",
        "sys_descr": "1.3.6.1.2.1.1.1.0",
        "sys_object_id": "1.3.6.1.2.1.1.2.0",
    }
    values = {}
    errors = []

    for field, oid in oid_map.items():
        value, error = _run_snmpget_value(
            address=address,
            community=community,
            oid=oid,
            port=port,
            version=version,
            timeout=timeout,
            retries=retries,
            executable=executable,
        )
        values[field] = value
        if error:
            errors.append(f"{field}: {error}")

    return SnmpHostMetadata(
        address=address,
        sys_name=values["sys_name"],
        sys_descr=values["sys_descr"],
        sys_object_id=values["sys_object_id"],
        error="; ".join(errors) if errors and not any(values.values()) else None,
    )


def build_identity_note(
    host,
    snmp_metadata=None,
    selected_mode=None,
    inferred_mode=None,
):
    """Build a stable identity note to attach to a discoverable."""
    lines = [
        "Network scan identity",
        f"Observed at: {datetime.now(UTC).isoformat()}",
        f"Address: {host.address}",
    ]
    if host.hostname:
        lines.append(f"Nmap hostname: {host.hostname}")
    if host.mac_address:
        lines.append(f"MAC address: {host.mac_address}")
    if host.vendor:
        lines.append(f"MAC vendor: {host.vendor}")
    if snmp_metadata:
        if snmp_metadata.sys_name:
            lines.append(f"SNMP sysName: {snmp_metadata.sys_name}")
        if snmp_metadata.sys_descr:
            lines.append(f"SNMP sysDescr: {snmp_metadata.sys_descr}")
        if snmp_metadata.sys_object_id:
            lines.append(f"SNMP sysObjectID: {snmp_metadata.sys_object_id}")
        if snmp_metadata.error:
            lines.append(f"SNMP probe: {snmp_metadata.error}")
    if inferred_mode:
        lines.append(f"Inferred mode: {inferred_mode}")
    elif selected_mode:
        lines.append(f"Fallback mode: {selected_mode}")
    return "\n".join(lines)


def merge_identity_note(existing_comments, identity_note):
    """Append a new identity note without duplicating the exact same text."""
    existing_comments = (existing_comments or "").strip()
    identity_note = (identity_note or "").strip()
    if not identity_note:
        return existing_comments
    if not existing_comments:
        return identity_note
    if identity_note in existing_comments:
        return existing_comments
    return f"{existing_comments}\n\n{identity_note}"


def candidate_to_summary(candidate):
    """Convert an enriched host candidate to JSON-serializable data."""
    summary = {
        "address": candidate.host.address,
        "hostname": candidate.host.hostname,
        "mac_address": candidate.host.mac_address,
        "vendor": candidate.host.vendor,
        "selected_mode": candidate.selected_mode,
        "inferred_mode": candidate.inferred_mode,
        "identity_note": candidate.identity_note,
    }
    if candidate.snmp_metadata:
        summary["snmp"] = {
            "sys_name": candidate.snmp_metadata.sys_name,
            "sys_descr": candidate.snmp_metadata.sys_descr,
            "sys_object_id": candidate.snmp_metadata.sys_object_id,
            "error": candidate.snmp_metadata.error,
        }
    return summary


def scan_host_candidates(
    target_specs,
    default_mode,
    snmp_community="",
    snmp_port=161,
    snmp_version="v2c",
    host_timeout=30,
    snmp_timeout=2,
    nmap_executable="nmap",
    snmp_executable="snmpget",
    snmp_fallback_max_hosts=256,
):
    """Run the scan and return enriched host candidates without persisting them."""
    normalized_targets = list(
        dict.fromkeys(
            normalize_target_spec(str(target).strip())
            for target in target_specs
            if str(target).strip()
        )
    )
    hosts = run_nmap_ping_scan(
        normalized_targets,
        host_timeout=host_timeout,
        executable=nmap_executable,
    )
    hosts_by_address = {host.address: host for host in hosts}
    snmp_metadata_by_address = {}

    if snmp_community:
        target_addresses = expand_target_spec_addresses(normalized_targets)
        if len(target_addresses) <= int(snmp_fallback_max_hosts):
            for address in target_addresses:
                if address in hosts_by_address:
                    continue
                snmp_metadata = run_snmp_identity_probe(
                    address=address,
                    community=snmp_community,
                    port=snmp_port,
                    version=snmp_version,
                    timeout=snmp_timeout,
                    executable=snmp_executable,
                )
                if not snmp_metadata_has_identity(snmp_metadata):
                    continue
                fallback_host = NmapHostResult(address=address, status="up")
                hosts.append(fallback_host)
                hosts_by_address[address] = fallback_host
                snmp_metadata_by_address[address] = snmp_metadata

    candidates = []
    for host in hosts:
        selected_mode = default_mode
        inferred_mode = None
        snmp_metadata = snmp_metadata_by_address.get(host.address)

        if snmp_community and snmp_metadata is None:
            snmp_metadata = run_snmp_identity_probe(
                address=host.address,
                community=snmp_community,
                port=snmp_port,
                version=snmp_version,
                timeout=snmp_timeout,
                executable=snmp_executable,
            )
            if snmp_metadata_has_identity(snmp_metadata):
                inferred_mode = infer_discovery_mode(
                    sys_descr=snmp_metadata.sys_descr,
                    sys_object_id=snmp_metadata.sys_object_id,
                    hostname=snmp_metadata.sys_name or host.hostname,
                    vendor=host.vendor,
                )
                if inferred_mode:
                    selected_mode = inferred_mode
        elif snmp_metadata_has_identity(snmp_metadata):
            inferred_mode = infer_discovery_mode(
                sys_descr=snmp_metadata.sys_descr,
                sys_object_id=snmp_metadata.sys_object_id,
                hostname=snmp_metadata.sys_name or host.hostname,
                vendor=host.vendor,
            )
            if inferred_mode:
                selected_mode = inferred_mode

        identity_note = build_identity_note(
            host,
            snmp_metadata=snmp_metadata,
            selected_mode=selected_mode,
            inferred_mode=inferred_mode,
        )
        candidates.append(
            ScannedHostCandidate(
                host=host,
                selected_mode=selected_mode,
                inferred_mode=inferred_mode,
                snmp_metadata=snmp_metadata,
                identity_note=identity_note,
            )
        )
    return candidates


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
    if "ios xe" in fingerprint or "ios-xe" in fingerprint or "catalyst" in fingerprint:
        return "netmiko_cisco_ios"
    if "ios xr" in fingerprint or "cisco xr" in fingerprint:
        return "netmiko_cisco_xr"
    if "nx-os" in fingerprint or "nxos" in fingerprint or "nexus" in fingerprint or "n9k" in fingerprint:
        return "netmiko_cisco_nxos"
    if "cisco ios" in fingerprint or "internetwork operating system" in fingerprint:
        return "netmiko_cisco_ios"
    if "arubaos-cx" in fingerprint or "aruba cx" in fingerprint or "aoscx" in fingerprint or "cx " in fingerprint:
        return "netmiko_aruba_aoscx"
    if "comware" in fingerprint or "h3c" in fingerprint:
        return "netmiko_hp_comware"
    if "procurve" in fingerprint or "arubaos-switch" in fingerprint or "provision" in fingerprint:
        return "netmiko_hp_procurve"
    if "huawei" in fingerprint or "vrp" in fingerprint or "quidway" in fingerprint:
        return "netmiko_huawei_vrp"
    if "allied telesis" in fingerprint or "alliedware plus" in fingerprint or "aw+" in fingerprint:
        return "netmiko_allied_telesis_awplus"
    if (
        "linux" in fingerprint
        or "unix" in fingerprint
        or "ubuntu" in fingerprint
        or "debian" in fingerprint
        or "centos" in fingerprint
        or "red hat" in fingerprint
        or "almalinux" in fingerprint
        or "rocky" in fingerprint
    ):
        return "netmiko_linux"
    if "cisco" in fingerprint:
        return "netmiko_cisco_ios"
    return None
