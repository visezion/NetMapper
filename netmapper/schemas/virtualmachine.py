"""Schema validation for VirtualMachine."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

from jsonschema import validate, FormatChecker

from virtualization.models import VirtualMachine
from virtualization.choices import VirtualMachineStatusChoices
from dcim.models import Device as Device_model, DeviceRole as DeviceRole_model

from netmapper import utils


def get_schema():
    """Return the JSON schema to validate VirtualMachine data."""
    return {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "transform": ["toUpperCase"],
            },
            "role_id": {
                "type": "integer",
                "enum": list(
                    DeviceRole_model.objects.all().values_list("id", flat=True)
                ),
            },
            "device_role_id": {
                "type": "integer",
                "enum": list(
                    DeviceRole_model.objects.all().values_list("id", flat=True)
                ),
            },
            "status": {
                "type": "string",
                "enum": list(VirtualMachineStatusChoices.values()),
            },
            "device_id": {
                "type": "integer",
                "enum": list(Device_model.objects.all().values_list("id", flat=True)),
            },
            "vcpus": {
                "type": "integer",
            },
            "memory": {
                "type": "integer",
            },
            "disk": {
                "type": "integer",
            },
        },
    }


def normalize_role_kwargs(kwargs):
    """Accept both legacy device_role_id and current role_id keys."""
    if "role_id" not in kwargs and "device_role_id" in kwargs:
        kwargs["role_id"] = kwargs["device_role_id"]
    return kwargs


def get_schema_create():
    """Return the JSON schema to validate new VirtualMachine objects."""
    schema = get_schema()
    schema["required"] = [
        "name",
        # "device_id",
        "status",
    ]
    return schema


def create(**kwargs):
    """Create a VirtualMachine.

    A VirtualMachine is created from hostname, status, and device_id.
    VirtualMachine is associated to a device, the device is associated
    to a cluster, and the cluster defines the platform.
    """
    kwargs = normalize_role_kwargs(kwargs)
    kwargs = utils.delete_empty_keys(kwargs)
    validate(kwargs, get_schema_create(), format_checker=FormatChecker())
    kwargs.pop("device_role_id", None)
    obj = utils.object_create(VirtualMachine, **kwargs)
    return obj


def get(name):
    """Return a VirtualMachine."""
    obj = utils.object_get_or_none(VirtualMachine, name=name)
    return obj


def get_list(**kwargs):
    """Get a list of VirtualMachine objects."""
    kwargs = normalize_role_kwargs(kwargs)
    validate(kwargs, get_schema(), format_checker=FormatChecker())
    kwargs.pop("device_role_id", None)
    result = utils.object_list(VirtualMachine, **kwargs)
    return result


def update(obj, status=None, **kwargs):
    """Update a VirtualMachine."""
    update_always = [
        "role_id",
        "cluster_id",
        "site_id",
        "device_id",
        "vcpus",
        "memory",
        "disk",
    ]

    if status and obj.status not in ["active", "offline"]:
        # Status is set and current status is not active or offline, adding to update_always
        kwargs.update(
            {
                "status": status,
            }
        )
        update_always.append("status")

    kwargs = normalize_role_kwargs(kwargs)
    kwargs = utils.delete_empty_keys(kwargs)
    validate(kwargs, get_schema(), format_checker=FormatChecker())
    kwargs.pop("device_role_id", None)
    kwargs_always = utils.filter_keys(kwargs, update_always)
    obj = utils.object_update(obj, **kwargs_always, force=True)
    return obj


def update_management(obj, discoverable_ip_address):
    """Update primary IP address if match the Discoverable IP address.

    Return True if management IP is set.
    """
    # Set management IP address
    for interface in obj.interfaces.filter(ip_addresses__isnull=False):
        # For each interface
        for ip_address_o in interface.ip_addresses.all():
            # For each configured IP address
            if discoverable_ip_address == str(ip_address_o.address.ip):
                obj = utils.object_update(obj, primary_ip4=ip_address_o)
                return True
    return False
