"""Blank the current database and load a specific scenario.

Usage:
/opt/netbox/venv/bin/python3 /opt/netbox/netbox/manage.py shell < lab_import.py
"""
from netmapper.tests.test import load_scenario

LAB_DIR = "netmapper/tests/netmiko_allied_telesis_awplus/lab1"

load_scenario(LAB_DIR)
