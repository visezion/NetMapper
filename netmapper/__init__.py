"""Main class."""
__author__ = "Andrea Dainese"
__contact__ = "oluwasusiv@gmail.com"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

import os
import shutil

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_migrate

from netbox.plugins import PluginConfig

MODULE_PATH = os.path.dirname(__file__)


def get_plugin_settings():
    """Return plugin settings when Django settings are available."""
    try:
        return settings.PLUGINS_CONFIG.get("netmapper", {})
    except ImproperlyConfigured:
        return {}


def get_ntc_templates_dir():
    """Resolve the ntc-templates directory without requiring configured settings."""
    return get_plugin_settings().get("NTC_TEMPLATES_DIR") or os.path.join(
        MODULE_PATH, "ntc_templates"
    )


def get_base_dir():
    """Return NetBox's base directory when available, else fall back locally."""
    try:
        return settings.BASE_DIR
    except ImproperlyConfigured:
        return MODULE_PATH


def sync_plugin_assets():
    """Create/update NetMapper script modules and optional legacy reports."""
    from core.models import DataSource, DataFile  # pylint: disable=import-outside-toplevel
    import extras.models as extras_models  # pylint: disable=import-outside-toplevel

    jobs_path = os.path.join(MODULE_PATH, "jobs")
    script_name = "netmapper_jobs"
    script_filename = f"{script_name}.py"
    report_name = "netmapper_reports"
    report_filename = f"{report_name}.py"

    ScriptModule = extras_models.ScriptModule
    ReportModule = getattr(extras_models, "ReportModule", None)

    try:
        jobs_ds_o = DataSource.objects.get(name="netmapper_jobs")
    except DataSource.DoesNotExist:  # pylint: disable=no-member
        jobs_ds_o = DataSource.objects.create(
            name="netmapper_jobs",
            type="local",
            source_url=jobs_path,
        )

    jobs_ds_o.sync()

    script_file_o = DataFile.objects.get(path=script_filename)
    try:
        script_o = ScriptModule.objects.get(file_path=script_filename)
    except ScriptModule.DoesNotExist:  # pylint: disable=no-member
        script_o = ScriptModule.objects.create(
            auto_sync_enabled=True,
            data_file=script_file_o,
            data_path=script_filename,
            data_source=jobs_ds_o,
            file_path=script_filename,
            file_root="scripts",
        )
    else:
        script_o.auto_sync_enabled = True
        script_o.data_file = script_file_o
        script_o.data_path = script_filename
        script_o.data_source = jobs_ds_o
        script_o.file_path = script_filename
        script_o.file_root = "scripts"

    shutil.copy(f"{jobs_path}/{script_filename}", settings.SCRIPTS_ROOT)
    script_o.sync()
    script_o.save()

    if ReportModule is not None:
        report_file_o = DataFile.objects.get(path=report_filename)
        try:
            report_o = ReportModule.objects.get(file_path=report_filename)
        except ReportModule.DoesNotExist:  # pylint: disable=no-member
            report_o = ReportModule.objects.create(
                auto_sync_enabled=True,
                data_file=report_file_o,
                data_path=report_filename,
                data_source=jobs_ds_o,
                file_path=report_filename,
                file_root="reports",
            )
        else:
            report_o.auto_sync_enabled = True
            report_o.data_file = report_file_o
            report_o.data_path = report_filename
            report_o.data_source = jobs_ds_o
            report_o.file_path = report_filename
            report_o.file_root = "reports"

        shutil.copy(f"{jobs_path}/{report_filename}", settings.REPORTS_ROOT)
        report_o.sync()
        report_o.save()


def sync_plugin_assets_after_migrate(sender, **kwargs):  # pylint: disable=unused-argument
    """Synchronize NetMapper assets after this plugin's migrations have run."""
    if getattr(sender, "name", None) != "netmapper":
        return
    sync_plugin_assets()


class NetmapperConfig(PluginConfig):
    """Configuration class."""

    name = "netmapper"
    verbose_name = "NetMapper"
    description = (
        "Automatically scan your network, detect device platforms and types, map "
        "physical connections, and bring discovered infrastructure into NetBox "
        "with structured discovery workflows."
    )
    version = "1.0.0"
    author = "Victor Ayodeji Oluwasusi"
    author_email = "oluwasusiv@gmail.com"
    base_url = "netmapper"
    min_version = "4.6.0"
    max_version = "4.6.99"
    homepage = "https://github.com/visezion/NetMapper"
    source_url = "https://github.com/visezion/NetMapper"
    documentation_url = "https://github.com/visezion/NetMapper#readme"
    support_url = "https://github.com/visezion/NetMapper/issues"
    license = "GNU General Public License v3.0"
    required_settings = []
    default_settings = {
        "MAX_INGESTED_LOGS": 25,
        "NMAP_EXECUTABLE": "nmap",
        "NMAP_HOST_TIMEOUT": 30,
        "NORNIR_LOG": os.path.join(get_base_dir(), "nornir.log"),
        "NORNIR_TIMEOUT": 300,
        "RAISE_ON_CDP_FAIL": True,
        "RAISE_ON_LLDP_FAIL": True,
        "ROLE_MAP": {},
        "SNMPGET_EXECUTABLE": "snmpget",
        "SNMP_FALLBACK_MAX_HOSTS": 256,
        "SNMP_TIMEOUT": 2,
        "SUBNET_SCAN_MAX_HOSTS": 4096,
        "SYNC_ON_STARTUP": False,
    }

    def ready(self):
        """Load signals and register asset synchronization hooks."""

        from netmapper import (  # noqa: F401 pylint: disable=import-outside-toplevel,unused-import
            signals,
        )

        post_migrate.connect(
            sync_plugin_assets_after_migrate,
            dispatch_uid="netmapper.sync_plugin_assets_after_migrate",
        )

        if get_plugin_settings().get("SYNC_ON_STARTUP"):
            sync_plugin_assets()

        super().ready()


config = NetmapperConfig  # pylint: disable=invalid-name

os.environ.setdefault("NET_TEXTFSM", get_ntc_templates_dir())
