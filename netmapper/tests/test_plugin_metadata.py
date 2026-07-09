"""Regression tests for package and plugin metadata consistency."""

from django.test import SimpleTestCase

from netmapper import NetmapperConfig, __version__
from netmapper.version import NETBOX_COMPATIBILITY, PLUGIN_VERSION


class PluginMetadataTest(SimpleTestCase):
    """Keep package metadata aligned for releases and deployments."""

    def test_plugin_config_uses_shared_version(self):
        """The plugin config and package version should not drift."""
        self.assertEqual(__version__, PLUGIN_VERSION)
        self.assertEqual(NetmapperConfig.version, PLUGIN_VERSION)

    def test_netbox_compatibility_string_is_available(self):
        """The shared compatibility string should remain importable."""
        self.assertEqual(NETBOX_COMPATIBILITY, "NetBox 4.6.x")
