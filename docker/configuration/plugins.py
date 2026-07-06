from os import environ


PLUGINS = [
    "netmapper",
]

PLUGINS_CONFIG = {
    "netmapper": {
        "NTC_TEMPLATES_DIR": "/opt/ntc-templates/ntc_templates/templates",
        "CREDENTIAL_FERNET_KEY": environ.get("NETMAPPER_CREDENTIAL_FERNET_KEY", ""),
    }
}
