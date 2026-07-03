"""Main class."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

import os
import shutil

from django.conf import settings

from netbox.plugins import PluginConfig

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG.get("netdoc", {})
NTC_TEMPLATES_DIR = PLUGIN_SETTINGS.get("NTC_TEMPLATES_DIR")
MODULE_PATH = os.path.dirname(__file__)


class NetdocConfig(PluginConfig):
    """Configuration class."""

    name = "netdoc"
    verbose_name = "NetDoc"
    description = "Automatic Network Documentation plugin for NetBox"
    version = "0.0.1-dev2"
    author = "Andrea Dainese"
    author_email = "andrea@adainese.it"
    base_url = "netdoc"
    required_settings = []
    default_settings = {
        "MAX_INGESTED_LOGS": 25,
        "NORNIR_LOG": f"{settings.BASE_DIR}/nornir.log",
        "NORNIR_TIMEOUT": 300,
        "RAISE_ON_CDP_FAIL": True,
        "RAISE_ON_LLDP_FAIL": True,
        "ROLE_MAP": {},
    }

    def ready(self):
        """Load signals and create scripts and optional legacy reports."""
        import sys  # noqa: F401 pylint: disable=import-outside-toplevel,unused-import

        from netdoc import (  # noqa: F401 pylint: disable=import-outside-toplevel,unused-import
            signals,
        )

        wsgi = "django.core.wsgi" in sys.modules

        if "migrate" not in sys.argv and (wsgi or "runserver" in sys.argv):
            from core.models import (  # noqa: F401 pylint: disable=import-outside-toplevel
                DataSource,
                DataFile,
            )
            import extras.models as extras_models  # pylint: disable=import-outside-toplevel

            ScriptModule = extras_models.ScriptModule

            # NetBox 4 removed legacy reports. Keep this optional for older NetBox versions.
            ReportModule = getattr(extras_models, "ReportModule", None)

            # Create/update data source for NetDoc jobs.
            jobs_path = os.path.join(MODULE_PATH, "jobs")
            try:
                jobs_ds_o = DataSource.objects.get(name="netdoc_jobs")
            except DataSource.DoesNotExist:  # pylint: disable=no-member
                jobs_ds_o = DataSource.objects.create(
                    name="netdoc_jobs",
                    type="local",
                    source_url=jobs_path,
                )

            jobs_ds_o.sync()

            # Create/update NetDoc scripts.
            script_name = "netdoc_scripts"
            script_filename = f"{script_name}.py"
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

            # Create/update NetDoc reports only if this NetBox version still supports ReportModule.
            if ReportModule is not None:
                report_name = "netdoc_reports"
                report_filename = f"{report_name}.py"
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

        super().ready()


config = NetdocConfig  # pylint: disable=invalid-name

# Setting NTC_TEMPLATES_DIR.
if not NTC_TEMPLATES_DIR:
    NTC_TEMPLATES_DIR = os.path.join(MODULE_PATH, "ntc_templates")

os.environ.setdefault("NET_TEXTFSM", NTC_TEMPLATES_DIR)
