# Repository Layout

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
  Discovery implementations per platform or framework.
- `netmapper/ingestors/`
  Parsed-output ingestion logic per command or template.
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
