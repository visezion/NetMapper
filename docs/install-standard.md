# Install into an Existing NetBox Instance

For the full lifecycle guide, including upgrade and rollback flow, see
[Installation and Updates](installation-and-updates.md).

Supported target:

- NetBox `4.6.x`
- validated in this repository against NetBox `4.6.4`

## 1. Install system tools

```bash
sudo apt-get update
sudo apt-get install -y git nmap snmp
```

## 2. Clone the repository

```bash
git clone https://github.com/visezion/NetMapper.git
cd NetMapper
git checkout <release-tag>  # for example: v1.0.2
```

Use `main` only when you intentionally want unreleased development changes.

## 3. Install the plugin package

```bash
python3 -m pip install .
```

If you manage NetBox dependencies with pinned requirements, keep this plugin on a NetBox `4.6.x` host.

## 4. Install or expose `ntc-templates`

Example:

```bash
git clone --depth=1 https://github.com/networktocode/ntc-templates /opt/ntc-templates
```

## 5. Enable the plugin in NetBox configuration

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

## 6. Apply migrations and static assets

```bash
python3 manage.py migrate
python3 manage.py collectstatic --no-input
```

## 7. Optional manual asset sync

```bash
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```

## 8. Restart NetBox services

Restart your web server, background worker, and any process manager services used by your NetBox deployment.

## 9. Update an existing NetBox installation

Use the release tag you want to deploy:

```bash
cd /path/to/NetMapper
git fetch --tags
git checkout <release-tag>
python3 -m pip install --upgrade .
python3 manage.py migrate
python3 manage.py collectstatic --no-input
python3 manage.py shell -c "from netmapper import sync_plugin_assets; sync_plugin_assets()"
```

Before a production upgrade:

- back up the NetBox database
- read the relevant [Upgrade Notes](upgrade-notes.md)
- restart the NetBox web and worker services after the update
