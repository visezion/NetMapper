"""Main class."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
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
        return settings.PLUGINS_CONFIG.get("netdoc", {})
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
    """Create/update NetDoc script modules and optional legacy reports."""
    from core.models import DataSource, DataFile  # pylint: disable=import-outside-toplevel
    import extras.models as extras_models  # pylint: disable=import-outside-toplevel

    jobs_path = os.path.join(MODULE_PATH, "jobs")
    script_name = "netdoc_scripts"
    script_filename = f"{script_name}.py"
    report_name = "netdoc_reports"
    report_filename = f"{report_name}.py"

    ScriptModule = extras_models.ScriptModule
    ReportModule = getattr(extras_models, "ReportModule", None)

    try:
        jobs_ds_o = DataSource.objects.get(name="netdoc_jobs")
    except DataSource.DoesNotExist:  # pylint: disable=no-member
        jobs_ds_o = DataSource.objects.create(
            name="netdoc_jobs",
            type="local",
            source_url=jobs_path,
        )

    jobs_ds_o.sync()

    script_file_o = DataFile.objects.get(path=script_filename)
    try:
        ScriptModule.objects.get(file_path=script_filename)
        shutil.copy(f"{jobs_path}/{script_filename}", settings.SCRIPTS_ROOT)
    except ScriptModule.DoesNotExist:  # pylint: disable=no-member
        script_o = ScriptModule.objects.create(
            auto_sync_enabled=True,
            data_file=script_file_o,
            data_path=script_filename,
            data_source=jobs_ds_o,
            file_path=script_filename,
            file_root="scripts",
        )
        script_o.sync()
        script_o.save()

    if ReportModule is not None:
        report_file_o = DataFile.objects.get(path=report_filename)
        try:
            ReportModule.objects.get(file_path=report_filename)
            shutil.copy(f"{jobs_path}/{report_filename}", settings.REPORTS_ROOT)
        except ReportModule.DoesNotExist:  # pylint: disable=no-member
            report_o = ReportModule.objects.create(
                auto_sync_enabled=True,
                data_file=report_file_o,
                data_path=report_filename,
                data_source=jobs_ds_o,
                file_path=report_filename,
                file_root="reports",
            )
            report_o.sync()
            report_o.save()


def sync_plugin_assets_after_migrate(sender, **kwargs):  # pylint: disable=unused-argument
    """Synchronize NetDoc assets after this plugin's migrations have run."""
    if getattr(sender, "name", None) != "netdoc":
        return
    sync_plugin_assets()


class NetdocConfig(PluginConfig):
    """Configuration class."""

    name = "netdoc"
    verbose_name = "NetDoc"
    description = "Automatic Network Documentation plugin for NetBox"
    version = "0.0.1-dev3"
    author = "Andrea Dainese"
    author_email = "andrea@adainese.it"
    base_url = "netdoc"
    required_settings = []
    default_settings = {
        "MAX_INGESTED_LOGS": 25,
        "NORNIR_LOG": os.path.join(get_base_dir(), "nornir.log"),
        "NORNIR_TIMEOUT": 300,
        "RAISE_ON_CDP_FAIL": True,
        "RAISE_ON_LLDP_FAIL": True,
        "ROLE_MAP": {},
        "SYNC_ON_STARTUP": False,
    }

    def ready(self):
        """Load signals and register asset synchronization hooks."""

        from netdoc import (  # noqa: F401 pylint: disable=import-outside-toplevel,unused-import
            signals,
        )

        post_migrate.connect(
            sync_plugin_assets_after_migrate,
            dispatch_uid="netdoc.sync_plugin_assets_after_migrate",
        )

        if get_plugin_settings().get("SYNC_ON_STARTUP"):
            sync_plugin_assets()

        super().ready()


config = NetdocConfig  # pylint: disable=invalid-name

os.environ.setdefault("NET_TEXTFSM", get_ntc_templates_dir())
