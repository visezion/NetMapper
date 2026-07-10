"""Helpers to seed NetBox devices directly from scan identity data."""

from __future__ import annotations

import ipaddress
import re

from netmapper import utils
from netmapper.schemas import (
    device as device_api,
    devicerole,
    devicetype,
    discoverable as discoverable_api,
    interface as interface_api,
    manufacturer as manufacturer_api,
)


ROLE_NAME_BY_INFERRED_ROLE = {
    "firewall": "Firewall",
    "phone": "Phone",
    "router": "Router",
    "server": "Server",
    "switch": "Access Switch",
    "wireless-access-point": "Wireless AP",
    "wireless-controller": "Wireless Controller",
}

KNOWN_MANUFACTURERS = [
    ("allied telesis", "Allied Telesis"),
    ("aruba", "Aruba"),
    ("cisco", "Cisco"),
    ("fortinet", "Fortinet"),
    ("grandstream", "Grandstream"),
    ("hpe", "HPE"),
    ("hp", "HP"),
    ("huawei", "Huawei"),
    ("juniper", "Juniper"),
    ("mikrotik", "MikroTik"),
    ("palo alto", "Palo Alto"),
    ("polycom", "Poly"),
    ("ubiquiti", "Ubiquiti"),
    ("vmware", "VMware"),
    ("yealink", "Yealink"),
]

MODEL_TOKEN_SKIPWORDS = {
    "software",
    "version",
    "release",
    "network",
    "technology",
    "communications",
    "communication",
    "device",
    "voice",
    "phone",
    "desktop",
    "ip",
    "system",
    "platform",
}


def candidate_requires_generic_seed(candidate):
    """Return True when scan identity exists but no supported discovery mode fits."""
    return bool(candidate.snmp_metadata and not candidate.inferred_mode)


def seed_device_from_scan_candidate(discoverable_o, candidate):
    """Create or update a generic NetBox device from scan identity metadata."""
    device_name = _infer_device_name(candidate, discoverable_o.address)
    manufacturer_name = _infer_manufacturer_name(candidate)
    model_name = _infer_model_name(candidate, manufacturer_name)

    role_o = _get_or_create_role(candidate.inferred_role)
    device_type_o = _get_or_create_device_type(
        manufacturer_name=manufacturer_name,
        model_name=model_name,
    )

    device_o = discoverable_o.device or device_api.get(device_name)
    created = False
    if not device_o:
        device_o = device_api.create(
            name=device_name,
            site_id=discoverable_o.site_id,
            role_id=role_o.id,
            device_type_id=device_type_o.id,
        )
        created = True
    else:
        device_api.update(
            device_o,
            role_id=role_o.id,
            device_type_id=device_type_o.id,
        )

    discoverable_api.update(
        discoverable_o,
        device_id=device_o.id,
    )

    interface_o = interface_api.get(
        device_id=device_o.id,
        label=utils.normalize_interface_label("mgmt0"),
    )
    if not interface_o:
        interface_o = interface_api.create(
            name="mgmt0",
            device_id=device_o.id,
            mac_address=candidate.host.mac_address,
        )
    else:
        interface_api.update(
            interface_o,
            name="mgmt0",
            mac_address=candidate.host.mac_address,
        )

    interface_api.update_addresses(
        interface_o,
        ip_addresses=[_primary_address_with_mask(discoverable_o.address)],
    )
    device_api.update_management(device_o, str(discoverable_o.address))
    return device_o, created


def _get_or_create_device_type(manufacturer_name=None, model_name=None):
    """Return a device type suited for a scan-seeded device."""
    manufacturer_name = manufacturer_name or "Unknown"
    manufacturer_o = manufacturer_api.get(name=manufacturer_name)
    if not manufacturer_o:
        manufacturer_o = manufacturer_api.create(name=manufacturer_name)

    if model_name:
        device_type_o = devicetype.get(
            model=model_name,
            manufacturer_id=manufacturer_o.id,
        )
        if not device_type_o:
            device_type_o = devicetype.create(
                model=model_name,
                manufacturer_id=manufacturer_o.id,
            )
        return device_type_o

    return device_api.create_manufacturer_and_model(manufacturer=manufacturer_name)


def _get_or_create_role(inferred_role):
    """Return a suitable device role for a scan-seeded device."""
    role_name = ROLE_NAME_BY_INFERRED_ROLE.get(inferred_role, "Unknown")
    role_o = devicerole.get(name=role_name)
    if not role_o:
        role_o = devicerole.create(name=role_name)
    return role_o


def _infer_device_name(candidate, address):
    """Return the best stable device name available from scan identity."""
    if candidate.snmp_metadata and candidate.snmp_metadata.sys_name:
        name = utils.normalize_hostname(candidate.snmp_metadata.sys_name)
        if name:
            return name
    if candidate.host.hostname:
        name = utils.normalize_hostname(candidate.host.hostname)
        if name:
            return name
    return str(address)


def _infer_manufacturer_name(candidate):
    """Infer an exact manufacturer string from scan identity."""
    sys_descr = (
        (candidate.snmp_metadata.sys_descr or "") if candidate.snmp_metadata else ""
    )
    vendor = candidate.host.vendor or ""
    fingerprint = f"{vendor} {sys_descr}".lower()
    for marker, display_name in KNOWN_MANUFACTURERS:
        if marker in fingerprint:
            return display_name

    cleaned_vendor = _clean_freeform_identity(vendor)
    if cleaned_vendor:
        return cleaned_vendor

    cleaned_descr_token = _clean_freeform_identity(sys_descr.split(" ")[0] if sys_descr else "")
    if cleaned_descr_token:
        return cleaned_descr_token
    return None


def _infer_model_name(candidate, manufacturer_name=None):
    """Extract a compact model token from sysDescr when possible."""
    if not candidate.snmp_metadata or not candidate.snmp_metadata.sys_descr:
        return None

    first_line = candidate.snmp_metadata.sys_descr.splitlines()[0].strip()
    if manufacturer_name and first_line.lower().startswith(manufacturer_name.lower()):
        first_line = first_line[len(manufacturer_name) :].strip(" ,:-")

    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9._/-]{2,}", first_line):
        normalized = token.strip(" ,;:()[]{}")
        if not normalized:
            continue
        if normalized.lower() in MODEL_TOKEN_SKIPWORDS:
            continue
        if any(character.isdigit() for character in normalized) or "-" in normalized:
            return normalized
    return None


def _clean_freeform_identity(value):
    """Collapse a freeform manufacturer string into a safe display name."""
    cleaned = re.sub(r"[^A-Za-z0-9 .&()+/-]+", " ", (value or "")).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return None
    return cleaned[:100]


def _primary_address_with_mask(address):
    """Return a host address with the narrowest valid prefix length."""
    ip_value = ipaddress.ip_address(str(address))
    if ip_value.version == 6:
        return f"{ip_value.compressed}/128"
    return f"{ip_value.compressed}/32"
