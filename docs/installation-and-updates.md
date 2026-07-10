# Installation and Updates

This guide is the main operator reference for deploying and upgrading
NetMapper.

Use a tagged release such as `v1.0.2` for production. Use `main` only when you
intentionally want unreleased development changes.

## Supported target

- NetBox `4.6.x`
- validated in this repository against NetBox `4.6.4`
- `netbox-docker` deployments validated against `5.0.1`

## Choose your deployment path

Use one of these:

- [Install with netbox-docker](install-docker.md) if you want the simplest
  supported deployment path
- [Install into an Existing NetBox Instance](install-standard.md) if you
  already operate NetBox outside Docker

## Before you install or update

For both fresh installs and upgrades:

1. Choose the release tag you want to deploy.
2. Confirm the target NetBox host is on NetBox `4.6.x`.
3. Back up your NetBox database before any upgrade.
4. If you use a custom `configuration.py` or plugin settings, keep a copy of
   them outside the plugin repository.

## Fresh installation

### netbox-docker

For a new Docker-based deployment:

```bash
mkdir -p ~/netbox-lab
cd ~/netbox-lab
git clone --branch 5.0.1 --depth 1 https://github.com/netbox-community/netbox-docker.git
git clone https://github.com/visezion/NetMapper.git

cd ~/netbox-lab/NetMapper
git checkout <release-tag>
./scripts/deploy_netbox_docker.sh <release-tag>
```

Then verify:

```bash
cd ~/netbox-lab/netbox-docker
docker compose ps
docker compose logs --tail=100 netbox
docker compose logs --tail=100 netbox-worker
docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
```

### Existing NetBox instance

For a non-Docker NetBox deployment:

```bash
git clone https://github.com/visezion/NetMapper.git
cd NetMapper
git checkout <release-tag>
python3 -m pip install .
```

Enable the plugin in NetBox:

```python
PLUGINS = [
    "netmapper",
]
```

If you use `ntc-templates`, also set:

```python
PLUGINS_CONFIG = {
    "netmapper": {
        "NTC_TEMPLATES_DIR": "/opt/ntc-templates/ntc_templates/templates",
    }
}
```

Apply the NetBox changes:

```bash
python3 manage.py migrate
python3 manage.py collectstatic --no-input
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```

Create the first NetBox superuser from the NetBox application directory:

```bash
python3 manage.py createsuperuser
```

Then restart the NetBox web and worker services used by your environment.

## Updating an existing deployment

### Recommended update workflow

Use this sequence for every release:

1. Read the relevant section in [Upgrade Notes](upgrade-notes.md).
2. Back up the NetBox database.
3. Fetch tags from GitHub.
4. Check out the target release tag.
5. Run the deployment or install commands for your environment.
6. Verify the plugin UI, scripts, and worker health after the upgrade.

### netbox-docker update

```bash
cd ~/netbox-lab/NetMapper
git fetch --tags
git checkout <release-tag>
./scripts/deploy_netbox_docker.sh <release-tag>
```

What this does:

- updates the repository to the selected tag
- skips `git pull` automatically when you are on a detached tag checkout
- rebuilds the NetBox image with the plugin
- restarts the NetBox and worker containers
- runs NetMapper asset synchronization inside NetBox

Useful options:

```bash
ALLOW_DIRTY=1 ./scripts/deploy_netbox_docker.sh <release-tag>
BUILD_NO_CACHE=1 ./scripts/deploy_netbox_docker.sh <release-tag>
NETBOX_DOCKER_DIR=/path/to/netbox-docker ./scripts/deploy_netbox_docker.sh <release-tag>
```

Use `ALLOW_DIRTY=1` only if you intentionally have local uncommitted changes.

### Existing NetBox instance update

```bash
cd /path/to/NetMapper
git fetch --tags
git checkout <release-tag>
python3 -m pip install --upgrade .
python3 manage.py migrate
python3 manage.py collectstatic --no-input
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```

Then restart the NetBox web and worker services.

If your NetBox deployment uses a Python virtual environment, activate that
environment before running `pip` or `manage.py`.

## Post-install or post-upgrade verification

Check these after deployment:

- the NetBox UI loads normally
- `Installed Plugins` shows `netmapper`
- NetMapper model pages load without reverse URL errors
- NetMapper script pages load correctly
- background jobs and worker processes remain healthy

Examples:

### netbox-docker

```bash
cd ~/netbox-lab/netbox-docker
docker compose ps
docker compose logs --tail=100 netbox
docker compose logs --tail=100 netbox-worker
```

### Existing NetBox instance

- review the NetBox application logs
- review the worker logs
- open the NetMapper navigation entries in the UI

## Rollback guidance

If an upgrade needs to be rolled back:

1. Restore the NetBox database backup.
2. Check out the previous known-good release tag.
3. Redeploy that tag using the same commands used for the upgrade.

For Docker:

```bash
cd ~/netbox-lab/NetMapper
git checkout <previous-release-tag>
./scripts/deploy_netbox_docker.sh <previous-release-tag>
```

For a standard installation:

```bash
cd /path/to/NetMapper
git checkout <previous-release-tag>
python3 -m pip install --upgrade .
python3 manage.py migrate
python3 manage.py collectstatic --no-input
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```

## Related documentation

- [Install with netbox-docker](install-docker.md)
- [Install into an Existing NetBox Instance](install-standard.md)
- [Upgrade Notes](upgrade-notes.md)
- [Configuration](configuration.md)
- [Troubleshooting](troubleshooting.md)
