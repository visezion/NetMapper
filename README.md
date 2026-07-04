# NetMapper for NetBox 4.6.x

NetMapper is a NetBox plugin for network discovery, topology mapping, and operational documentation.

This repository is maintained as the `visezion/NetMapper` fork and is targeted at NetBox `4.6.x`, including `netbox-docker` deployments.

## Maintainer

- Name: Victor Ayodeji Oluwasusi
- Email: oluwasusiv@gmail.com
- Repository: `https://github.com/visezion/NetMapper`

## Current scope

NetMapper currently provides:

- multi-vendor CLI discovery through Nornir and Netmiko
- subnet/range seeding with `nmap` plus optional SNMP-assisted mode inference
- device, interface, IP, route, ARP, MAC, and topology ingestion
- L2, L3, and site diagrams inside NetBox
- a Docker deployment flow for `netbox-docker`

## Compatibility

- NetBox: `4.6.x`
- Python: follows the NetBox runtime used by the target environment
- Deployments tested in this repo: `netbox-docker`

## Quick start with netbox-docker

Clone both repositories side by side:

```bash
git clone https://github.com/netbox-community/netbox-docker.git
git clone https://github.com/visezion/NetMapper.git
```

Deploy NetBox with NetMapper:

```bash
cd NetMapper
./scripts/deploy_netbox_docker.sh main
```

If your paths differ:

```bash
NETBOX_DOCKER_DIR=/path/to/netbox-docker \
NETMAPPER_PATH=/path/to/NetMapper \
./scripts/deploy_netbox_docker.sh main
```

## Standard NetBox install

Install the plugin into an existing NetBox environment:

```bash
git clone https://github.com/visezion/NetMapper.git
cd NetMapper
python3 -m pip install .
```

Add the plugin to your NetBox configuration:

```python
PLUGINS = ["netmapper"]

PLUGINS_CONFIG = {
    "netmapper": {
        "NTC_TEMPLATES_DIR": "/opt/ntc-templates/ntc_templates/templates",
    }
}
```

Then run:

```bash
python3 manage.py migrate
python3 manage.py collectstatic --no-input
python3 manage.py runserver
```

## Notes

- The package and plugin name are now `netmapper`.
- The deployment tooling still accepts a legacy `NETDOC_PATH` environment variable as a fallback to ease migration from older checkouts.
- Historical source attribution and licensing remain in the codebase because this project is a maintained fork, not a greenfield rewrite.

## Network Seeding

Use the `Scan subnet or range` script job to:

- scan one or more IPs, CIDRs, or full IP ranges with `nmap`
- optionally probe responsive hosts with SNMP v2c for `sysName` and `sysDescr`
- infer a best-fit discovery mode when possible
- create or update `Discoverable` records and optionally queue the normal discovery workflow

## Planned work

- streamlined fresh-server install documentation
- deeper SNMP enrichment for VLAN/interface/neighbor modeling
- dedicated subnet discovery UI beyond NetBox script jobs
