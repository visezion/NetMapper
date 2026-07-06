# How to Use NetMapper

Typical first-time usage:

1. Install and enable the plugin.
2. Create one or more `Credentials`.
3. Create or import `Discoverables`.
4. Assign the correct discovery mode to each discoverable.
5. Run `Discover`.
6. Review `Logs`.
7. Run `Ingest` if needed.
8. Review devices, interfaces, ARP, MAC, routes, and diagrams.

For subnet or range discovery:

1. Create a discovery `Credential`.
2. Optionally create an `SNMP Credential`.
3. Open `NetMapper > Network Scan`.
4. Enter IPs, ranges, or CIDRs.
5. Run `Preview` or `Dry Run`.
6. Run the actual scan.
7. Review `Scan History`.
8. Confirm the queued discovery job completes for the resulting discoverables.
9. Review the created or updated devices, interfaces, IP addresses, VLANs, neighbors, and topology data in NetBox.
