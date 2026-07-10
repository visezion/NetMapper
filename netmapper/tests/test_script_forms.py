"""Regression tests for NetMapper script form rendering."""

from django.test import SimpleTestCase

from netmapper.jobs.netmapper_jobs import (
    AddDiscoverable,
    Discover,
    Ingest,
    ScanNetwork,
)


class ScriptFormUrlTest(SimpleTestCase):
    """Ensure plugin-backed script selectors use stable API URLs."""

    def test_scan_network_plugin_selectors_use_explicit_api_urls(self):
        """The scan form must not depend on inferred plugin API route names."""
        form = ScanNetwork().as_form()

        self.assertEqual(
            form.fields["credential"].widget.attrs["data-url"],
            "/api/plugins/netmapper/credential/",
        )
        self.assertEqual(
            form.fields["snmp_credential"].widget.attrs["data-url"],
            "/api/plugins/netmapper/snmpcredential/",
        )

    def test_other_plugin_selectors_use_explicit_api_urls(self):
        """Other script selectors should be renderable without URL inference."""
        add_form = AddDiscoverable().as_form()
        discover_form = Discover().as_form()
        ingest_form = Ingest().as_form()

        self.assertEqual(
            add_form.fields["credential"].widget.attrs["data-url"],
            "/api/plugins/netmapper/credential/",
        )
        self.assertEqual(
            discover_form.fields["discoverables"].widget.attrs["data-url"],
            "/api/plugins/netmapper/discoverable/",
        )
        self.assertEqual(
            ingest_form.fields["discoverables"].widget.attrs["data-url"],
            "/api/plugins/netmapper/discoverable/",
        )
