# Discovery Workflows

## Standard Device Discovery

Standard discovery uses:

- `Discoverable`
- `Credential`
- discovery mode
- discoverer module
- `DiscoveryLog`
- ingestor module

Execution flow:

1. `netmapper/tasks.py` builds a Nornir inventory.
2. The target host is grouped by discovery mode.
3. A discoverer in `netmapper/discoverers/` runs device commands.
4. Raw output is saved in `DiscoveryLog`.
5. Parsing and ingest logic convert data into NetBox objects.

## Subnet or Range Discovery

Subnet or range discovery uses:

- `Network Scan` UI
- `ScanNetwork` script job
- `netmapper/network_discovery.py`
- optional SNMP enrichment
- `NetworkScanRecord`

Execution flow:

1. `nmap` scans the requested subnet, CIDR, or IP range for responsive hosts.
2. NetMapper optionally tests SNMP against those hosts to gather identity details.
3. The plugin infers the best discovery mode from SNMP and Nmap identity data.
4. `Discoverable` records are created or updated for each responsive host.
5. The normal `Discover` workflow is queued automatically unless disabled.
6. Nornir and Netmiko connect over SSH or the protocol defined by the discovery mode.
7. Platform-specific discoverers run show commands.
8. TextFSM and NTC templates parse supported output into structured data.
9. Ingestors write the parsed data into NetBox models.

Resulting NetBox updates can include:

- devices
- interfaces
- IP addresses
- VLANs
- ARP and MAC tables
- LLDP or CDP neighbor relationships
- cable links when the parsed topology data is sufficient

Capabilities around this workflow:

- preview normalized targets
- dry-run scan execution
- full scan execution
- scan history
- identity note persistence on discoverables

## Credential Testing

The UI supports:

- discovery credential test
- SNMP credential test

Use these before a production discovery run to catch:

- bad passwords
- bad enable secrets
- unreachable targets
- invalid SNMP community values
