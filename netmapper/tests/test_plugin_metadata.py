"""Regression tests for package and plugin metadata consistency."""

from django.test import SimpleTestCase

from netmapper import NetmapperConfig, __version__
from netmapper.version import NETBOX_COMPATIBILITY, get_plugin_version


class PluginMetadataTest(SimpleTestCase):
    """Keep package metadata aligned for releases and deployments."""

    def test_plugin_config_uses_shared_version(self):
        """The plugin config and runtime package version should not drift."""
        self.assertEqual(__version__, get_plugin_version())
        self.assertEqual(NetmapperConfig.version, __version__)
        self.assertTrue(__version__)

    def test_netbox_compatibility_string_is_available(self):
        """The shared compatibility string should remain importable."""
        self.assertEqual(NETBOX_COMPATIBILITY, "NetBox 4.6.x")
