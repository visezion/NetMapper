"""
NetMapper packaging configuration.

Build with:
    python -m build
Validate with:
    python -m twine check dist/*
"""

__author__ = "Victor Ayodeji Oluwasusi"
__contact__ = "oluwasusiv@gmail.com"
__copyright__ = "Copyright 2026, Victor Ayodeji Oluwasusi"
__license__ = "GPLv3"
from pathlib import Path

from setuptools import find_namespace_packages, setup

README = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
VERSION_NS = {}
exec(
    Path(__file__).with_name("netmapper").joinpath("version.py").read_text(
        encoding="utf-8"
    ),
    VERSION_NS,
)
PLUGIN_VERSION = VERSION_NS["PLUGIN_VERSION"]
NETBOX_COMPATIBILITY = VERSION_NS["NETBOX_COMPATIBILITY"]

setup(
    name="netmapper",
    version=PLUGIN_VERSION,
    description=(
        "Auto-discover network devices, identify platforms, map links, and sync "
        "physical infrastructure into NetBox"
    ),
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/visezion/NetMapper",
    author="Victor Ayodeji Oluwasusi",
    author_email="oluwasusiv@gmail.com",
    license="GNU General Public License v3.0",
    python_requires=">=3.10",
    install_requires=[
        "ipaddress==1.0.23",
        "jsonschema==3.2.0",
        "macaddress==2.0.2",
        "n2g==0.3.3",
        "netmiko==4.7.0",
        "nornir==3.3.0",
        "nornir_netmiko==1.0.1",
        "nornir_utils",
        "ouilookup==0.2.4",
        "python-slugify",
        "pyvmomi==8.0.1.0.1",
        "setuptools==80.9.0",
        "xmltodict==0.13.0",
    ],
    packages=find_namespace_packages(include=["netmapper*"]),
    package_data={
        "netmapper": [
            "jobs/*.py",
            "library/*.yml",
            "ntc_templates/*",
            "static/netmapper/css/*",
            "static/netmapper/img/*",
            "static/netmapper/js/*",
            "templates/netmapper/*.html",
            "templates/netmapper/buttons/*.html",
            "templates/netmapper/htmx/*.html",
        ]
    },
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords=[
        "netbox",
        "netbox-plugin",
        "network-discovery",
        "topology-mapping",
        "netbox-4.6",
    ],
    project_urls={
        "NetBox Compatibility": "https://github.com/visezion/NetMapper#netmapper-for-netbox-46x",
        "Documentation": "https://github.com/visezion/NetMapper#readme",
        "Issues": "https://github.com/visezion/NetMapper/issues",
        "Version History": "https://github.com/visezion/NetMapper/commits/main",
        "Releases": "https://github.com/visezion/NetMapper/releases",
        "Source": "https://github.com/visezion/NetMapper",
    },
)
