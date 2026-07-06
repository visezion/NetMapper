# Install into an Existing NetBox Instance

## 1. Install system tools

```bash
sudo apt-get update
sudo apt-get install -y git nmap snmp
```

## 2. Clone the repository

```bash
git clone https://github.com/visezion/NetMapper.git
cd NetMapper
```

## 3. Install the plugin package

```bash
python3 -m pip install .
```

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
