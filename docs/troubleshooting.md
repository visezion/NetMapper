# Troubleshooting

## `nmap` or `snmpget` not found

Install the system packages and verify:

```bash
which nmap
which snmpget
```

## NetBox is running but the browser cannot open it

If the containers are healthy but you cannot open NetBox in the browser, make sure the host port is published.

Create or edit the override file:

```bash
nano docker-compose.override.yml
```

Put this inside:

```yaml
services:
  netbox:
    ports:
      - "8000:8080"
```

Save the file:

- `CTRL + O`
- `ENTER`
- `CTRL + X`

Then restart the stack:

```bash
docker compose down
docker compose up -d
```

After that, open:

```text
http://SERVER_IP:8000
```

## Cisco IOS enable mode failures

If enable mode fails, verify that the `Credential` includes the correct `enable_password`.

## Scan created discoverables but not devices

That usually means the seeding step worked but the later discovery or ingestion path did not complete or was not queued.

## SNMP works but subnet or range scan misses some hosts

If ICMP or default Nmap host discovery is filtered in your environment, NetMapper performs an automatic SNMP fallback for small scans when an SNMP credential is supplied.

## Empty diagrams

Check:

- diagram filters
- discovery completion
- data ingestion
- cable relationships for L2 diagrams

## Plugin jobs or reports not visible

Run:

```bash
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```
