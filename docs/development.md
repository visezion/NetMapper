# Development and Validation

## Local Docker development

This repository includes a full Docker-based development flow through:

- `docker/Dockerfile-Plugins`
- `docker/docker-compose.override.yml`
- `scripts/deploy_netbox_docker.sh`

## Quick syntax checks

```bash
python -m py_compile netmapper/models.py netmapper/forms.py netmapper/views.py
```

## Validation used for this repository

Recent work was validated against a live NetBox `4.6.4` plus `netbox-docker 5.0.1` deployment, including:

- plugin startup
- migrations
- credential test pages
- SNMP credential test pages
- network scan preview
- network scan dry-run
- queued subnet or range scan
- scan history pages
