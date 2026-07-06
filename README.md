# NetMapper for NetBox 4.6.x

NetMapper is a NetBox plugin for network discovery, topology mapping, operational documentation, and subnet/range seeding.

This repository is maintained as the `visezion/NetMapper` fork and is currently targeted at NetBox `4.6.x`, including `netbox-docker` deployments.

## Table of Contents

- [Overview](#overview)
- [Maintainer](#maintainer)
- [Compatibility](#compatibility)
- [Features](#features)
- [Supported Discovery Modes](#supported-discovery-modes)
- [How NetMapper Works](#how-netmapper-works)
- [Repository Layout](#repository-layout)
- [Requirements](#requirements)
- [Install with netbox-docker](#install-with-netbox-docker)
- [Install into an Existing NetBox Instance](#install-into-an-existing-netbox-instance)
- [Configuration](#configuration)
- [How to Use NetMapper](#how-to-use-netmapper)
- [UI Guide](#ui-guide)
- [Discovery Workflows](#discovery-workflows)
- [Scan History and Identity Notes](#scan-history-and-identity-notes)
- [Diagrams](#diagrams)
- [How to Understand the Repository](#how-to-understand-the-repository)
- [How to Add or Extend Functionality](#how-to-add-or-extend-functionality)
- [Troubleshooting](#troubleshooting)
- [Development and Validation](#development-and-validation)
- [Upgrade Notes](#upgrade-notes)
- [License and Origin](#license-and-origin)

## Overview

NetMapper extends NetBox with:

- network discovery and ingestion
- multi-vendor command collection
- topology and relationship mapping
- subnet/range seeding using `nmap`
- optional SNMP-assisted platform inference
- stored credential management for discovery and scanning
- diagram generation inside NetBox

This fork is focused on working cleanly with modern NetBox `4.6.x` and `netbox-docker`.

## Maintainer

- Name: Victor Ayodeji Oluwasusi
- Email: oluwasusiv@gmail.com
- Repository: `https://github.com/visezion/NetMapper`

## Compatibility

This repository has been updated and validated against:

- NetBox `4.6.4`
- `netbox-docker` `5.0.1`
- plugin package name `netmapper`

Deployment targets covered by this repository:

- `netbox-docker`
- standard NetBox Python installations

## Features

NetMapper currently provides:

- multi-vendor discovery through Nornir and Netmiko
- Palo Alto XML API discovery support
- VMware vSphere inventory discovery support
- discoverable device management inside NetBox
- discovery job execution and logging
- parsed command ingestion into NetBox models
- ARP, MAC address table, and routing table ingestion
- L2, L3, and site diagrams inside NetBox
- subnet/range scanning with `nmap`
- optional SNMP-assisted platform inference during scans
- stored SNMP credentials in the UI
- scan preview, dry-run, and scan history
- credential test pages for discovery and SNMP credentials
- persistent scan identity notes stored on discoverables

## Supported Discovery Modes

The current discovery mode set includes:

- Allied Telesis AW+
- Aruba AOS-CX
- Cisco IOS XE
- Cisco IOS XE over Telnet
- Cisco NX-OS
- Cisco XR
- HPE Comware
- HPE ProCurve
- HPE ProCurve over Telnet
- Huawei VRP
- Linux
- Palo Alto Networks NGFW via XML API
- VMware vSphere

## How NetMapper Works

At a high level, NetMapper works in four layers:

1. `Discoverable` records define what NetMapper should connect to.
2. A discovery mode maps each target to a protocol/framework implementation.
3. Discoverers collect raw output and create `DiscoveryLog` entries.
4. Ingestors parse and store useful data in NetBox models.

There is also a separate subnet/range scanning path:

1. The `Network Scan` page or `Scan subnet or range` job accepts IPs, CIDRs, or ranges.
2. `nmap` finds responsive hosts.
3. Optional SNMP probes collect `sysName`, `sysDescr`, and `sysObjectID`.
4. NetMapper selects an inferred or fallback mode.
5. `Discoverable` records are created or updated.
6. The normal discovery workflow can be queued automatically.

## Repository Layout

Key paths:

- `netmapper/`
  Main plugin package.
- `netmapper/models.py`
  Plugin database models.
- `netmapper/views.py`
  UI views and scan workflow endpoints.
- `netmapper/forms.py`
  NetBox forms, filters, and scan form definitions.
- `netmapper/tables.py`
  NetBox table definitions.
- `netmapper/filtersets.py`
  List and search filters.
- `netmapper/navigation.py`
  NetBox menu integration.
- `netmapper/tasks.py`
  Main discovery execution flow.
- `netmapper/utils.py`
  Shared helpers for parsing, command execution, and job spawning.
- `netmapper/discoverers/`
  Discovery implementations per platform/framework.
- `netmapper/ingestors/`
  Parsed-output ingestion logic per command/template.
- `netmapper/jobs/netmapper_jobs.py`
  NetBox script jobs used by the plugin.
- `netmapper/network_discovery.py`
  `nmap` and SNMP scan helpers.
- `netmapper/credential_testing.py`
  Credential verification helpers.
- `netmapper/templates/`
  Plugin UI templates.
- `netmapper/tests/`
  Test coverage for helper logic and plugin behavior.
- `docker/Dockerfile-Plugins`
  Docker image build for `netbox-docker`.
- `docker/docker-compose.override.yml`
  Compose override for plugin builds.
- `docker/configuration/plugins.py`
  Example Docker plugin configuration.
- `scripts/deploy_netbox_docker.sh`
  Deployment helper for Docker installs.

## Requirements

### Runtime Requirements

- NetBox `4.6.x`
- Python version matching the target NetBox runtime
- `nmap`
- `snmpget`
- `ntc-templates`

### netbox-docker Prerequisites

For a fresh Ubuntu server using the Docker deployment path, install:

```bash
sudo apt-get update
sudo apt-get install -y git docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
newgrp docker
```

Notes:

- run `newgrp docker` or start a new shell session before using `docker compose`
- if your distribution uses different package names, install Docker Engine plus the Docker Compose v2 plugin

### Python Requirements

Installed by `setup.py`:

- `netmiko`
- `nornir`
- `nornir_netmiko`
- `nornir_utils`
- `jsonschema`
- `xmltodict`
- `n2g`
- `ouilookup`
- `pyvmomi`

## Install with netbox-docker

This is the easiest supported deployment path.

### 1. Clone the repositories side by side

```bash
mkdir -p ~/netbox-lab
cd ~/netbox-lab
git clone https://github.com/netbox-community/netbox-docker.git
git clone https://github.com/visezion/NetMapper.git
```

Expected layout:

```text
~/netbox-lab/netbox-docker
~/netbox-lab/NetMapper
```

### 2. Deploy NetBox with NetMapper

```bash
cd ~/netbox-lab/NetMapper
./scripts/deploy_netbox_docker.sh main
```

What the script does:

- fetches and fast-forwards this repository
- builds a fresh NetBox image with NetMapper installed
- installs `git`, `nmap`, `snmp`, and `ntc-templates`
- recreates NetBox and worker containers
- waits for container health checks
- runs NetMapper asset synchronization

Notes:

- the first startup on a fresh database can take several minutes while NetBox applies migrations and builds its initial cache
- this repository overrides the upstream NetBox healthcheck to allow slower first responses on small lab or VM hosts

### 3. Deploy when your paths differ

```bash
cd /path/to/NetMapper
NETBOX_DOCKER_DIR=/path/to/netbox-docker \
NETMAPPER_PATH=/path/to/NetMapper \
./scripts/deploy_netbox_docker.sh main
```

### 4. Deploy from a dirty tree for development only

```bash
ALLOW_DIRTY=1 ./scripts/deploy_netbox_docker.sh main
```

## Install into an Existing NetBox Instance

### 1. Install system tools

```bash
sudo apt-get update
sudo apt-get install -y git nmap snmp
```

### 2. Clone the repository

```bash
git clone https://github.com/visezion/NetMapper.git
cd NetMapper
```

### 3. Install the plugin package

```bash
python3 -m pip install .
```

### 4. Install or expose `ntc-templates`

Example:

```bash
git clone --depth=1 https://github.com/networktocode/ntc-templates /opt/ntc-templates
```

### 5. Enable the plugin in NetBox configuration

```python
PLUGINS = [
    "netmapper",
]

PLUGINS_CONFIG = {
    "netmapper": {
        "NTC_TEMPLATES_DIR": "/opt/ntc-templates/ntc_templates/templates",
    }
}
```

### 6. Apply migrations and static assets

```bash
python3 manage.py migrate
python3 manage.py collectstatic --no-input
```

### 7. Optional manual asset sync

```bash
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```

### 8. Restart NetBox services

Restart your web server, background worker, and any process manager services used by your NetBox deployment.

## Configuration

Supported `PLUGINS_CONFIG["netmapper"]` settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `CREDENTIAL_FERNET_KEY` | empty, falls back to NetBox `SECRET_KEY` derivation | dedicated Fernet key for stored discovery/SNMP secrets |
| `NTC_TEMPLATES_DIR` | bundled fallback or `/opt/ntc-templates/...` in Docker | TextFSM template directory |
| `MAX_INGESTED_LOGS` | `25` | log ingestion limit |
| `NMAP_EXECUTABLE` | `nmap` | binary used for subnet/range scanning |
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
| `SYNC_ON_STARTUP` | `False` | sync jobs/reports automatically on startup |

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

Credential security notes:

- NetMapper now supports a dedicated `CREDENTIAL_FERNET_KEY` so stored discovery and SNMP secrets do not have to rely solely on NetBox's Django `SECRET_KEY`.
- If `CREDENTIAL_FERNET_KEY` is not set, NetMapper keeps the legacy behavior for backward compatibility.
- Existing encrypted values remain readable because NetMapper falls back to the legacy `SECRET_KEY`-derived key during decryption.

## How to Use NetMapper

Typical first-time usage:

1. Install and enable the plugin.
2. Create one or more `Credentials`.
3. Create or import `Discoverables`.
4. Assign the correct discovery mode to each discoverable.
5. Run `Discover`.
6. Review `Logs`.
7. Run `Ingest` if needed.
8. Review devices, interfaces, ARP, MAC, routes, and diagrams.

For subnet/range discovery:

1. Create a discovery `Credential`.
2. Optionally create an `SNMP Credential`.
3. Open `NetMapper > Network Scan`.
4. Enter IPs, ranges, or CIDRs.
5. Run `Preview` or `Dry Run`.
6. Run the actual scan.
7. Review `Scan History`.
8. Launch or verify queued discovery for the resulting discoverables.

## UI Guide

The plugin adds a `NetMapper` menu in NetBox.

Main sections:

- `Credentials`
  Discovery credentials for CLI/API connections.
- `SNMP Credentials`
  Stored SNMP v2c credentials for scan enrichment.
- `Network Scan`
  Dedicated scan page for IPs, CIDRs, and ranges.
- `Scan History`
  Historical records for scan runs.
- `Discoverables`
  Targets queued for discovery.
- `Logs`
  Raw and parsed discovery output.
- `ARP Table`
- `MAC Address Table`
- `Routing Table`
- `Diagrams`

## Discovery Workflows

### Standard Device Discovery

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

### Subnet/Range Discovery

Subnet/range discovery uses:

- `Network Scan` UI
- `ScanNetwork` script job
- `netmapper/network_discovery.py`
- optional SNMP enrichment
- `NetworkScanRecord`

Capabilities:

- preview normalized targets
- dry-run scan execution
- full scan execution
- scan history
- identity note persistence on discoverables

### Credential Testing

The UI now supports:

- discovery credential test
- SNMP credential test

Use these before a production discovery run to catch:

- bad passwords
- bad enable secrets
- unreachable targets
- invalid SNMP community values

## Scan History and Identity Notes

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

## Diagrams

NetMapper includes:

- L2 diagrams
- L3 diagrams
- site diagrams

Important behavior:

- L2 diagrams depend on cabled interfaces
- L3 diagrams depend on interface/IP data
- site diagrams depend on discovered and modeled relationships

If a diagram is empty:

- verify filters
- verify data ingestion completed
- verify cable relationships for L2 views

## How to Understand the Repository

If you are new to the codebase, read it in this order:

1. `netmapper/__init__.py`
   Plugin registration, default settings, asset sync.
2. `netmapper/models.py`
   Core data model.
3. `netmapper/views.py`
   Main UI behavior.
4. `netmapper/forms.py`
   User input and filter handling.
5. `netmapper/tasks.py`
   Main discovery execution flow.
6. `netmapper/utils.py`
   Shared helpers.
7. `netmapper/dictionaries.py`
   Discovery mode definitions and behavior maps.
8. `netmapper/discoverers/`
   Per-platform collection logic.
9. `netmapper/ingestors/`
   Per-command data ingestion logic.
10. `netmapper/jobs/netmapper_jobs.py`
    NetBox script jobs for operators.

Mental model:

- discoverers collect
- logs store
- ingestors interpret
- models persist
- views/forms present and trigger workflows

## How to Add or Extend Functionality

### Add a new discovery mode

1. Add the mode definition to `DiscoveryModeChoices.MODES` in `netmapper/dictionaries.py`.
2. Create a matching discoverer in `netmapper/discoverers/`.
3. Add platform-specific command logic.
4. Add matching ingestors in `netmapper/ingestors/` for supported outputs.
5. Test that `tasks.discovery()` can reach the discoverer and ingest the results.

### Add a new parsed command ingestor

1. Identify the command template name used by the discoverer.
2. Add a module under `netmapper/ingestors/`.
3. Implement ingestion logic that maps parsed output into NetBox models.
4. Verify that `utils.log_ingest()` can resolve and run the ingestor.

### Add a new scan inference rule

1. Update `infer_discovery_mode()` in `netmapper/network_discovery.py`.
2. Add or extend tests in `netmapper/tests/test_network_discovery.py`.
3. Validate with dry-run or queued scan history.

### Add a new UI page

1. Create or update a view in `netmapper/views.py`.
2. Add forms and filters in `netmapper/forms.py` if needed.
3. Add tables in `netmapper/tables.py` if needed.
4. Add routes in `netmapper/urls.py`.
5. Add menu items in `netmapper/navigation.py`.
6. Add templates under `netmapper/templates/netmapper/`.

### Add a new model

1. Add the model to `netmapper/models.py`.
2. Create a migration in `netmapper/migrations/`.
3. Add views, forms, filtersets, and tables if the object needs UI support.
4. Add tests and validate startup and migration flow.

## Troubleshooting

### `nmap` or `snmpget` not found

Install the system packages and verify:

```bash
which nmap
which snmpget
```

### Cisco IOS enable mode failures

If enable mode fails, verify that the `Credential` includes the correct `enable_password`.

### Scan created discoverables but not devices

That usually means the seeding step worked but the later discovery/ingestion path did not complete or was not queued.

### SNMP works but subnet/range scan misses some hosts

If ICMP or default Nmap host discovery is filtered in your environment, NetMapper now performs an automatic SNMP fallback for small scans when an SNMP credential is supplied.

### Empty diagrams

Check:

- diagram filters
- discovery completion
- data ingestion
- cable relationships for L2 diagrams

### Plugin jobs or reports not visible

Run:

```bash
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```

## Development and Validation

### Local Docker development

This repository includes a full Docker-based development flow through:

- `docker/Dockerfile-Plugins`
- `docker/docker-compose.override.yml`
- `scripts/deploy_netbox_docker.sh`

### Quick syntax checks

```bash
python -m py_compile netmapper/models.py netmapper/forms.py netmapper/views.py
```

### Validation used for this repository

Recent work was validated against a live NetBox `4.6.4` + `netbox-docker 5.0.1` deployment, including:

- plugin startup
- migrations
- credential test pages
- SNMP credential test pages
- network scan preview
- network scan dry-run
- queued subnet/range scan
- scan history pages

## Upgrade Notes

- Older deployments may still reference `netdoc`; this fork uses `netmapper`.
- The deployment script still accepts legacy `NETDOC_PATH` as a fallback for older automation.
- Historical source attribution remains in the codebase because this project is a maintained fork.

## License and Origin

This repository is a maintained fork of the original NetDoc project. Historical copyright and license headers remain in the source files.

Review the repository license and upstream attribution before redistributing modified builds.
