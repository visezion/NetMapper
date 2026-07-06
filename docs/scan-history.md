# Scan History and Identity Notes

Each scan history record stores:

- target input
- normalized targets
- invalid targets
- status
- dry-run flag
- responsive host count
- created, updated, and reused counts
- SNMP failure count
- result rows for responsive hosts

Each discoverable can also store scan-derived `identity_notes`, such as:

- Nmap hostname
- MAC vendor
- SNMP `sysName`
- SNMP `sysDescr`
- inferred mode
