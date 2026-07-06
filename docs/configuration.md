# Configuration

Supported `PLUGINS_CONFIG["netmapper"]` settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `CREDENTIAL_FERNET_KEY` | empty, falls back to NetBox `SECRET_KEY` derivation | dedicated Fernet key for stored discovery or SNMP secrets |
| `NTC_TEMPLATES_DIR` | bundled fallback or `/opt/ntc-templates/...` in Docker | TextFSM template directory |
| `MAX_INGESTED_LOGS` | `25` | log ingestion limit |
| `NMAP_EXECUTABLE` | `nmap` | binary used for subnet or range scanning |
| `NMAP_HOST_TIMEOUT` | `30` | per-host Nmap timeout in seconds |
| `NORNIR_LOG` | `<BASE_DIR>/nornir.log` | Nornir log path |
| `NORNIR_TIMEOUT` | `300` | Nornir task timeout |
| `RAISE_ON_CDP_FAIL` | `True` | fail hard on CDP problems |
| `RAISE_ON_LLDP_FAIL` | `True` | fail hard on LLDP problems |
| `ROLE_MAP` | `{}` | diagram role overrides |
| `SNMPGET_EXECUTABLE` | `snmpget` | binary used for SNMP probes |
| `SNMP_FALLBACK_MAX_HOSTS` | `256` | max target count for automatic SNMP fallback when Nmap host discovery misses devices |
| `SNMP_TIMEOUT` | `2` | SNMP timeout in seconds |
| `SUBNET_SCAN_MAX_HOSTS` | `4096` | scan safety cap |
| `SYNC_ON_STARTUP` | `False` | sync jobs or reports automatically on startup |

Example:

```python
PLUGINS_CONFIG = {
    "netmapper": {
        "CREDENTIAL_FERNET_KEY": "replace-with-a-fernet-key-from-python-cryptography",
        "NTC_TEMPLATES_DIR": "/opt/ntc-templates/ntc_templates/templates",
        "NMAP_EXECUTABLE": "nmap",
        "SNMPGET_EXECUTABLE": "snmpget",
        "NMAP_HOST_TIMEOUT": 30,
        "SNMP_FALLBACK_MAX_HOSTS": 256,
        "SNMP_TIMEOUT": 2,
        "SUBNET_SCAN_MAX_HOSTS": 4096,
        "SYNC_ON_STARTUP": False,
    }
}
```

## Credential security notes

- NetMapper supports a dedicated `CREDENTIAL_FERNET_KEY` so stored discovery and SNMP secrets do not have to rely solely on NetBox's Django `SECRET_KEY`.
- If `CREDENTIAL_FERNET_KEY` is not set, NetMapper keeps the legacy behavior for backward compatibility.
- Existing encrypted values remain readable because NetMapper falls back to the legacy `SECRET_KEY`-derived key during decryption.
