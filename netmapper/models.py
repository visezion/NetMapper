"""Models (ORM).

Define ORM models for NetMapper objects:
* A Discoverable is a device willed to be discovered using a specific mode.
* Credential is associated to one or more Discoverables.
* A DiscoveryLog is the output for a specific discovery command executed in a Discoverable.
"""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

import re
import json
import base64
from xml.parsers.expat import ExpatError
import xmltodict
from cryptography.fernet import Fernet, InvalidToken
from OuiLookup import OuiLookup

from django.db import models
from django.urls import reverse
from django.conf import settings

from ipam.fields import IPAddressField
from dcim.fields import MACAddressField
from netbox.models import NetBoxModel

from netmapper.utils import (
    parse_netmiko_output,
    is_command_supported,
)
from netmapper.dictionaries import (
    CONFIG_COMMANDS,
    CREDENTIAL_ENCRYPTED_FIELDS,
    SNMP_CREDENTIAL_ENCRYPTED_FIELDS,
    FAILURE_OUTPUT,
    DiagramModeChoices,
    DiscoveryModeChoices,
    RouteTypeChoices,
)

SECRET_KEY = settings.SECRET_KEY.encode("utf-8")
FERNET_KEY = base64.urlsafe_b64encode(SECRET_KEY.ljust(32)[:32])


#
# ARPEntry model
#


class ArpTableEntry(NetBoxModel):
    """
    Model for ArpTableEntry.

    Each ARP seen on each network interface is
    counted. One IP Address can be associated to one MAC Address. One MAC
    Address can be associated to multiple IP Addresses.
    """

    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )
    ip_address = IPAddressField(help_text="IPv4 address", editable=False)
    mac_address = MACAddressField(help_text="MAC Address", editable=False)
    vendor = models.CharField(
        max_length=255, blank=True, null=True, help_text="Vendor", editable=False
    )  #: Vendor (from OUI)
    virtual_interface = models.ForeignKey(
        to="virtualization.VMInterface",
        on_delete=models.CASCADE,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )

    class Meta:
        """Database metadata."""

        ordering = ["ip_address"]
        unique_together = [
            "interface",
            "ip_address",
            "mac_address",
            "virtual_interface",
        ]
        verbose_name = "ARP table entry"
        verbose_name_plural = "ARP table entries"

    @property
    def meta_interface(self):
        """
        Define meta_interface property.

        meta_interface return Device or VM, if set.
        """
        if self.interface:
            return self.interface
        if self.virtual_interface:
            return self.virtual_interface
        return None

    @property
    def meta_role(self):
        """
        Role meta_role property.

        meta_role return device/vm role, if set.
        """
        if (
            self.interface
            and self.interface.device.role  # pylint: disable=no-member
        ):
            return self.interface.device.role.name  # pylint: disable=no-member
        if (
            self.virtual_interface
            and self.virtual_interface.virtual_machine.role  # pylint: disable=no-member
        ):
            return (
                self.virtual_interface.virtual_machine.role.name  # pylint: disable=no-member
            )
        return None

    @property
    def meta_device(self):
        """
        Define meta_device property.

        meta_device return Device or VM, if set.
        """
        if self.interface:
            return self.interface.device  # pylint: disable=no-member
        if self.virtual_interface:
            return self.virtual_interface.virtual_machine  # pylint: disable=no-member
        return None

    def __str__(self):
        """Return a human readable name when the object is printed."""
        if self.interface:
            return f"{self.ip_address} has {self.mac_address} at {self.interface}"
        return f"{self.ip_address} has {self.mac_address} at {self.virtual_interface}"

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:arptableentry", args=[self.pk])

    def save(self, *args, **kwargs):
        """Set vendor field when saving."""
        self.vendor = list(
            OuiLookup().query(str(self.mac_address)).pop().values()
        ).pop()
        super().save(*args, **kwargs)


#
# Credential model
#


class Credential(NetBoxModel):
    """Model for Credential."""

    name = models.CharField(max_length=100)
    enable_password = models.TextField(blank=True)
    password = models.TextField(blank=True)
    username = models.CharField(
        max_length=100,
        blank=True,
    )
    verify_cert = models.BooleanField(default=True, help_text="Validate certificate")

    class Meta:
        """Database metadata."""

        ordering = ["name"]
        unique_together = ["name"]
        verbose_name = "Credential"
        verbose_name_plural = "Credentials"

    def __str__(self):
        """Return a human readable name when the object is printed."""
        return str(self.name)

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:credential", args=[self.pk])

    def get_secrets(self):
        """Get clear text password."""
        fernet_o = Fernet(FERNET_KEY)
        secrets = {}
        for field in CREDENTIAL_ENCRYPTED_FIELDS:
            original_secret = getattr(self, field)
            if original_secret:
                # Check if already decrypted
                try:
                    secret = fernet_o.decrypt(
                        original_secret.encode()  # pylint: disable=no-member
                    ).decode()
                except InvalidToken:
                    secret = original_secret
            else:
                secret = None
            secrets[field] = secret
        return secrets


class SnmpVersionChoices(models.TextChoices):
    """Supported SNMP protocol versions for lightweight scan enrichment."""

    V2C = "v2c", "SNMP v2c"


class SnmpCredential(NetBoxModel):
    """Model for stored SNMP credentials used by network scans."""

    name = models.CharField(max_length=100)
    version = models.CharField(
        max_length=10,
        choices=SnmpVersionChoices.choices,
        default=SnmpVersionChoices.V2C,
    )
    community = models.TextField(blank=True)
    port = models.PositiveIntegerField(default=161)

    class Meta:
        """Database metadata."""

        ordering = ["name"]
        unique_together = ["name"]
        verbose_name = "SNMP credential"
        verbose_name_plural = "SNMP credentials"

    def __str__(self):
        """Return a human readable name when the object is printed."""
        return str(self.name)

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:snmpcredential", args=[self.pk])

    def get_secrets(self):
        """Get clear text SNMP secrets."""
        fernet_o = Fernet(FERNET_KEY)
        secrets = {}
        for field in SNMP_CREDENTIAL_ENCRYPTED_FIELDS:
            original_secret = getattr(self, field)
            if original_secret:
                try:
                    secret = fernet_o.decrypt(
                        original_secret.encode()  # pylint: disable=no-member
                    ).decode()
                except InvalidToken:
                    secret = original_secret
            else:
                secret = None
            secrets[field] = secret
        return secrets


class NetworkScanStatusChoices(models.TextChoices):
    """Execution state for network scan history records."""

    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class NetworkScanRecord(NetBoxModel):
    """Historical record for subnet/range scans launched from NetMapper."""

    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.CASCADE,
        related_name="+",
    )
    credential = models.ForeignKey(
        to=Credential,
        on_delete=models.PROTECT,
        related_name="+",
    )
    snmp_credential = models.ForeignKey(
        to=SnmpCredential,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )
    default_mode = models.CharField(
        max_length=30,
        choices=DiscoveryModeChoices,
    )
    targets = models.TextField()
    normalized_targets = models.JSONField(default=list, blank=True)
    invalid_targets = models.JSONField(default=list, blank=True)
    filters = models.CharField(max_length=255, blank=True)
    filter_type = models.CharField(max_length=20, blank=True)
    discover_now = models.BooleanField(default=True)
    overwrite_mode = models.BooleanField(default=False)
    dry_run = models.BooleanField(default=False)
    store_identity_notes = models.BooleanField(default=True)
    max_hosts = models.PositiveIntegerField(default=4096)
    nmap_host_timeout = models.PositiveIntegerField(default=30)
    snmp_timeout = models.PositiveIntegerField(default=2)
    estimated_host_count = models.PositiveIntegerField(default=0)
    responsive_hosts_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    reused_count = models.PositiveIntegerField(default=0)
    snmp_failures_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=NetworkScanStatusChoices.choices,
        default=NetworkScanStatusChoices.QUEUED,
    )
    job_id = models.CharField(max_length=100, blank=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    summary = models.JSONField(default=dict, blank=True)
    results = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        """Database metadata."""

        ordering = ["-created"]
        verbose_name = "Network scan"
        verbose_name_plural = "Network scans"

    def __str__(self):
        """Return a human readable name when the object is printed."""
        mode = "Dry run" if self.dry_run else "Scan"
        return f"{mode} {self.created:%Y-%m-%d %H:%M:%S} for {self.site}"

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:networkscanrecord", args=[self.pk])


#
# Diagram model
#


class Diagram(NetBoxModel):
    """Model for Diagram."""

    details = models.JSONField(
        default=dict,
    )  #: Vis.Js Details in JSON format
    device_roles = models.ManyToManyField(
        to="dcim.DeviceRole",
        related_name="+",
        blank=True,
    )
    mode = models.CharField(
        max_length=30,
        choices=DiagramModeChoices,
    )
    name = models.CharField(max_length=100)
    sites = models.ManyToManyField(
        to="dcim.Site",
        related_name="+",
        blank=True,
    )
    vrfs = models.ManyToManyField(
        to="ipam.VRF",
        related_name="+",
        blank=True,
    )
    include_global_vrf = models.BooleanField(
        default=False
    )  #: Always include Global VRF (None)

    class Meta:
        """Database metadata."""

        ordering = ["name"]
        unique_together = [
            "name",
        ]
        verbose_name = "Diagram"
        verbose_name_plural = "Diagrams"

    def __str__(self):
        """Return a human readable name when the object is printed."""
        return str(self.name)

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:diagram", args=[self.pk])


#
# Discoverable model
#


class Discoverable(NetBoxModel):
    """Model for Discoverable."""

    address = models.GenericIPAddressField()
    identity_notes = models.TextField(
        blank=True,
        help_text="Stored Nmap/SNMP identity observations from network scans.",
    )
    device = models.OneToOneField(
        to="dcim.Device",
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )
    credential = models.ForeignKey(
        to=Credential,
        on_delete=models.PROTECT,
        related_name="discoverables",
    )
    mode = models.CharField(
        max_length=30,
        choices=DiscoveryModeChoices,
    )
    discoverable = models.BooleanField(
        default=False
    )  #: New created devices have discoverable=False by default (e.g. if created from CDP/LLDP)
    last_discovered_at = models.DateTimeField(blank=True, null=True, editable=False)
    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.CASCADE,
        related_name="+",
    )
    vm = models.OneToOneField(
        to="virtualization.VirtualMachine",
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )

    class Meta:
        """Database metadata."""

        ordering = ["mode", "address"]
        unique_together = ["address", "mode"]
        verbose_name = "Device"
        verbose_name_plural = "Devices"

    @property
    def meta_device(self):
        """
        Define meta_device property.

        meta_device return Device or VM, if set.
        """
        if self.device:
            return self.device
        if self.vm:
            return self.vm
        return None

    def __str__(self):
        """Return a human readable name when the object is printed."""
        return f"{self.address} via {self.mode}"

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:discoverable", args=[self.pk])


#
# Discovery log model
#


class DiscoveryLog(NetBoxModel):
    """Model for DiscoveryLog."""

    command = models.CharField(
        max_length=255, editable=False
    )  #: Exact CMD used to discover
    configuration = models.BooleanField(
        default=False,
        editable=False,
    )
    discoverable = models.ForeignKey(
        to=Discoverable,
        on_delete=models.CASCADE,
        related_name="discoverylogs",
        editable=False,
    )
    details = models.JSONField(
        default=dict,
        editable=False,
    )  #: Details in JSON format stored within Nornir task name
    order = models.IntegerField(default=128)  #: Order to ingest (lower is sooner)
    parsed_output = models.JSONField(default=list, editable=False)
    raw_output = models.JSONField(
        default=dict,
    )
    template = models.CharField(
        max_length=255, editable=False
    )  #: Template used to ingest parsed_output
    success = models.BooleanField(
        default=False, editable=False
    )  # True if excuting request return OK and raw_output is valid (avoid command not found)
    supported = models.BooleanField(
        default=True, editable=False
    )  #: False if output is unsupported (won't be ingested)
    parsed = models.BooleanField(
        default=False, editable=False
    )  #: True if parsing raw_output return a valid JSON
    ingested = models.BooleanField(
        default=False, editable=False
    )  #: True if all data are ingested without errors

    class Meta:
        """Database metadata."""

        ordering = ["created"]
        verbose_name = "Log"
        verbose_name_plural = "Logs"

    @property
    def meta_device(self):
        """
        Define meta_device property.

        meta_device return Device or VM, if set.
        """
        if self.discoverable.device:  # pylint: disable=no-member
            return self.discoverable.device  # pylint: disable=no-member
        if self.discoverable.vm:  # pylint: disable=no-member
            return self.discoverable.vm  # pylint: disable=no-member
        return None

    def __str__(self):
        """Return a human readable name when the object is printed."""
        return f"{self.command} at {self.created}"

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:discoverylog", args=[self.pk])

    def parse(self):
        """Parse raw_output."""
        self.success = False
        self.parsed = False
        self.parsed_output = ""

        # Check if the command is a configuration file
        configuration = False
        if self.template != "HOSTNAME":
            for regex in CONFIG_COMMANDS:
                if re.search(regex, self.command):
                    configuration = True
            self.configuration = configuration

        # Check if the command is supported
        discoverer = DiscoveryModeChoices.MODES.get(
            self.discoverable.mode  # pylint: disable=no-member
        ).get("discovery_script")
        self.supported = is_command_supported(
            discoverer, self.template  # pylint: disable=no-member
        )

        # Check if the output is completed successfully
        for regex in FAILURE_OUTPUT:
            if re.search(regex, self.raw_output):
                # Command failed -> skip parsing
                return
        self.success = True

        # Get framework (e.g. netmiko) and NTC Template (e.g. cisco_ios)
        framework = DiscoveryModeChoices.MODES.get(
            self.discoverable.mode  # pylint: disable=no-member
        ).get("framework")
        ntc_template = DiscoveryModeChoices.MODES.get(
            self.discoverable.mode  # pylint: disable=no-member
        ).get("ntc_template")

        if self.template == "HOSTNAME":
            # Logs tracking hostnames are parsed during ingestion phase
            parsed = True
            parsed_output = ""
        else:
            if framework == "netmiko":
                parsed_output, parsed = parse_netmiko_output(
                    self.raw_output, ntc_template, self.template
                )
            elif framework == "json":
                try:
                    parsed = True
                    parsed_output = json.loads(self.raw_output)
                except TypeError as exc:
                    parsed = False
                    parsed_output = str(exc)
                except json.decoder.JSONDecodeError as exc:
                    parsed = False
                    parsed_output = str(exc)
            elif framework == "xml":
                try:
                    parsed = True
                    parsed_output = xmltodict.parse(self.raw_output)
                except TypeError as exc:
                    parsed = False
                    parsed_output = str(exc)
                except ExpatError as exc:
                    parsed = False
                    parsed_output = str(exc)
            else:
                raise ValueError(f"Framework {framework} not implemented")

        self.parsed_output = parsed_output
        self.parsed = parsed

    def save(self, *args, **kwargs):
        """Set details when creating."""
        if not self.pk:
            # Check if command is supported
            mode = self.discoverable.mode  # pylint: disable=no-member
            framework = DiscoveryModeChoices.MODES.get(mode).get("framework")
            platform = DiscoveryModeChoices.MODES.get(mode).get("platform")
            protocol = DiscoveryModeChoices.MODES.get(mode).get("protocol")

            # Update log details
            details = self.details
            details["framework"] = framework
            details["platform"] = platform
            details["protocol"] = protocol
            self.details = details

            # Parse
            self.parse()

        super().save(*args, **kwargs)


#
# MacAddressTableEntry model
#


class MacAddressTableEntry(NetBoxModel):
    """Model for MacAddressTableEntry.

    Each MAC Address seen on each network
    interface is counted. One IP Address can be associated to one AC
    Address. One MAC Address can be associated to multiple IP Addresses.
    """

    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="+",
        editable=False,
    )
    mac_address = MACAddressField(help_text="MAC Address", editable=False)
    vendor = models.CharField(
        max_length=255, blank=True, null=True, help_text="Vendor", editable=False
    )  #: Vendor (from OUI)
    vvid = models.IntegerField(help_text="VLAN ID")  #: VLAN ID (TAG)

    class Meta:
        """Database metadata."""

        ordering = ["mac_address", "vvid"]
        unique_together = ["interface", "mac_address", "vvid"]
        verbose_name = "MAC Address table entry"
        verbose_name_plural = "MAC Address table entries"

    def __str__(self):
        """Return a human readable name when the object is printed."""
        return f"{self.mac_address} is at {self.interface}"

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:macaddresstableentry", args=[self.pk])

    def save(self, *args, **kwargs):
        """Set vendor field when saving."""
        self.vendor = list(
            OuiLookup().query(str(self.mac_address)).pop().values()
        ).pop()
        super().save(*args, **kwargs)


#
# RouteTableEntry model
#


class RouteTableEntry(NetBoxModel):
    """Model for RouteTableEntry.

    Each route has a destination, type (connected, static...),
    nexthop_ip and/or nexthop_if, distance (administrative), metric.
    """

    destination = IPAddressField(help_text="Destination network", editable=False)
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="+",
        blank=True,
        null=True,
    )
    distance = models.IntegerField(blank=True, null=True, editable=False)
    metric = models.BigIntegerField(blank=True, null=True, editable=False)
    nexthop_ip = IPAddressField(
        help_text="IPv4 address",
        editable=False,
        blank=True,
        null=True,
    )
    nexthop_if = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )
    nexthop_virtual_if = models.ForeignKey(
        to="virtualization.VMInterface",
        on_delete=models.CASCADE,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )
    protocol = models.CharField(
        max_length=30,
        choices=RouteTypeChoices,
        editable=False,
    )
    vrf = models.ForeignKey(
        to="ipam.VRF",
        on_delete=models.CASCADE,
        related_name="+",
        editable=False,
        blank=True,
        null=True,
    )
    vm = models.ForeignKey(
        to="virtualization.VirtualMachine",
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )

    class Meta:
        """Database metadata."""

        ordering = ["device", "protocol", "metric"]
        unique_together = [
            "device",
            "destination",
            "distance",
            "metric",
            "protocol",
            "vrf",
            "nexthop_if",
            "nexthop_virtual_if",
            "nexthop_ip",
            "vm",
        ]
        verbose_name = "Route"
        verbose_name_plural = "Routes"

    @property
    def meta_nexthop_if(self):
        """
        Define meta_nexthop_if property.

        meta_nexthop_if return Device or VM, if set.
        """
        if self.nexthop_virtual_if:
            return self.nexthop_virtual_if
        if self.nexthop_if:
            return self.nexthop_if
        return None

    @property
    def meta_device(self):
        """
        Define meta_device property.

        meta_device return Device or VM, if set.
        """
        if self.device:
            return self.device
        if self.vm:
            return self.vm
        return None

    def __str__(self):
        """Return a human readable name when the object is printed."""
        if self.nexthop_ip:
            return (
                f"{self.destination} {self.protocol}"
                + f" [{self.distance}/{self.metric}] via {self.nexthop_ip}"
            )
        # Assuming nexthop_if
        return (
            f"{self.destination} {self.protocol}"
            + f" [{self.distance}/{self.metric}] at {self.nexthop_if}"
        )

    def get_absolute_url(self):
        """Return the absolute url."""
        return reverse("plugins:netmapper:routetableentry", args=[self.pk])
