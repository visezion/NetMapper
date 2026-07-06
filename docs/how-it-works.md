# How NetMapper Works

At a high level, NetMapper works in four layers:

1. `Discoverable` records define what NetMapper should connect to.
2. A discovery mode maps each target to a protocol or framework implementation.
3. Discoverers collect raw output and create `DiscoveryLog` entries.
4. Ingestors parse and store useful data in NetBox models.

There is also a separate subnet or range scanning path:

1. The `Network Scan` page or `Scan subnet or range` job accepts IPs, CIDRs, or ranges.
2. `nmap` finds responsive hosts in the requested subnet or IP range.
3. Optional SNMP probes check reachable hosts and collect `sysName`, `sysDescr`, and `sysObjectID`.
4. NetMapper uses Nmap and SNMP identity data to infer the best available discovery platform or falls back to the selected default mode.
5. `Discoverable` records are created or updated with the selected discovery mode and attached credentials.
6. NetMapper queues the standard SSH discovery workflow for those discoverables.
7. Nornir and Netmiko connect to the device and run the platform command set.
8. TextFSM and NTC templates parse supported command output.
9. Ingestors create or update NetBox objects such as devices, interfaces, IP addresses, VLANs, neighbors, and cables when the collected data supports those relationships.
