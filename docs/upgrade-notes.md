# Upgrade Notes

## NetMapper 1.0.1

NetMapper `1.0.1` is a maintenance release for NetBox `4.6.x` focused on
stability, compatibility, and upgrade safety.

### Fixed

- Fixed a `DeviceType` creation collision during inventory ingest when a
  matching manufacturer and slug already existed in NetBox.
- Fixed SNMP credential URL naming compatibility so NetBox pages and script
  forms no longer fail with `NoReverseMatch` for `snmpcredential-list`.
- Fixed internal SNMP credential navigation and action links to use the
  NetBox-compatible route names.
- Fixed `netbox-docker` deployments from a Git tag or detached HEAD. The
  deploy script now skips `git pull` automatically when deploying a tagged
  release such as `v1.0.1`.
- Fixed CI pipeline issues:
  - formatting failures in `views.py`
  - the `pylint` workflow trying to install `netmapper` from PyPI instead of
    the checked-out repository

### Improved

- Added regression coverage for legacy `DeviceType` slug reuse during model
  matching.
- Added regression coverage for SNMP credential URL compatibility between
  hyphenated and underscored route names.
- Improved the Docker deployment flow so branch-based deployments still
  fast-forward normally while tag-based deployments work without special flags.

### Compatibility

- Supported NetBox versions remain `4.6.x`.
- Validated against NetBox `4.6.4`.

### Why Upgrade

Upgrade to `1.0.1` to avoid:

- SNMP credential page and script reverse URL errors
- inventory ingest failures caused by duplicate `DeviceType` slug conflicts
- deployment failures caused by `git pull` running on a tag checkout

### Upgrade Steps

#### netbox-docker

```bash
cd ~/netbox-lab/NetMapper
git fetch --tags
git checkout v1.0.1
./scripts/deploy_netbox_docker.sh v1.0.1
```

Use `ALLOW_DIRTY=1` only if you intentionally have local uncommitted changes:

```bash
ALLOW_DIRTY=1 ./scripts/deploy_netbox_docker.sh v1.0.1
```

#### Standard NetBox installation

```bash
cd /path/to/NetMapper
git fetch --tags
git checkout v1.0.1
python3 -m pip install --upgrade .
python3 manage.py migrate
python3 manage.py collectstatic --no-input
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```

Restart the NetBox web and worker services after the upgrade.

## Legacy Notes

- Older deployments may still reference `netdoc`; this fork uses `netmapper`.
- The deployment script still accepts legacy `NETDOC_PATH` as a fallback for
  older automation.
- Historical source attribution remains in the codebase because this project is
  a maintained fork.
