"""Version helpers for NetMapper package and plugin metadata."""

from importlib.metadata import PackageNotFoundError, version as package_version

NETBOX_COMPATIBILITY = "NetBox 4.6.x"


def get_plugin_version():
    """Resolve the package version from installed metadata or Git tags."""
    try:
        return package_version("netmapper")
    except PackageNotFoundError:
        pass

    try:
        from setuptools_scm import get_version
    except ImportError:
        return "0+unknown"

    try:
        return get_version(
            root="..",
            relative_to=__file__,
            tag_regex=r"^v(?P<version>.+)$",
        )
    except Exception:  # pylint: disable=broad-except
        return "0+unknown"
