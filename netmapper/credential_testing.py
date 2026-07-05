"""Connectivity tests for stored discovery and SNMP credentials."""

import requests
from netmiko import ConnectHandler

from netmapper.dictionaries import DiscoveryModeChoices
from netmapper.network_discovery import run_snmp_identity_probe


def test_snmp_credential(snmp_credential, address, timeout=2, executable="snmpget"):
    """Test an SNMP credential against a target and return structured results."""
    secrets = snmp_credential.get_secrets()
    metadata = run_snmp_identity_probe(
        address=address,
        community=secrets.get("community") or "",
        port=snmp_credential.port,
        version=snmp_credential.version,
        timeout=timeout,
        executable=executable,
    )
    return {
        "success": not metadata.error,
        "address": address,
        "details": {
            "sys_name": metadata.sys_name,
            "sys_descr": metadata.sys_descr,
            "sys_object_id": metadata.sys_object_id,
        },
        "error": metadata.error,
    }


def test_discovery_credential(credential, address, mode, timeout=10):
    """Test a stored discovery credential against a target and return details."""
    mode_data = DiscoveryModeChoices.MODES.get(mode)
    if not mode_data:
        raise ValueError(f"Unsupported discovery mode: {mode}")

    framework = mode_data.get("framework")
    secrets = credential.get_secrets()

    if framework == "netmiko":
        params = {
            "device_type": mode_data.get("platform"),
            "host": address,
            "username": credential.username,
            "password": secrets.get("password"),
            "timeout": timeout,
            "auth_timeout": timeout,
            "banner_timeout": timeout,
        }
        if secrets.get("enable_password"):
            params["secret"] = secrets.get("enable_password")
        connection = ConnectHandler(**params)
        try:
            login_prompt = connection.find_prompt()
            enable_prompt = None
            if secrets.get("enable_password"):
                connection.enable()
                enable_prompt = connection.find_prompt()
            return {
                "success": True,
                "address": address,
                "mode": mode,
                "details": {
                    "framework": framework,
                    "login_prompt": login_prompt,
                    "enable_prompt": enable_prompt,
                },
                "error": None,
            }
        finally:
            connection.disconnect()

    if framework == "xml" and mode == "xml_panw_ngfw":
        api_key = secrets.get("password")
        if not api_key:
            raise ValueError("This Palo Alto mode expects the credential password field to contain an API key.")
        url = (
            f"https://{address}/api/?type=op&cmd=<show><system><info></info></system></show>"
            f"&key={api_key}"
        )
        response = requests.get(
            url,
            timeout=timeout,
            verify=credential.verify_cert,
        )
        if response.status_code != 200:
            raise ValueError(f"HTTP {response.status_code}: {response.text[:200]}")
        if 'status="success"' not in response.text:
            raise ValueError(response.text[:400])
        return {
            "success": True,
            "address": address,
            "mode": mode,
            "details": {
                "framework": framework,
                "status_code": response.status_code,
            },
            "error": None,
        }

    raise ValueError(f"Credential testing is not implemented for framework '{framework}'.")
