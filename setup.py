"""
NetMapper PYPI setup file.

Install with: python3 setup.py install
Develop with: python3 setup.py develop
Make it available on PIP with:
    python3 setup.py sdist
    pip3 install twine
    twine upload dist/*
"""

__author__ = "Andrea Dainese"
__contact__ = "oluwasusiv@gmail.com"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"
__version__ = "0.1.0"

from setuptools import find_packages, setup

setup(
    name="netmapper",
    version=__version__,
    description="Network discovery, topology mapping, and operational documentation for NetBox",
    url="https://github.com/visezion/NetMapper",
    author="Victor Ayodeji Oluwasusi",
    author_email="oluwasusiv@gmail.com",
    license="GNU v3.0",
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
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
    ],
    project_urls={
        "Source": "https://github.com/visezion/NetMapper",
    },
)
