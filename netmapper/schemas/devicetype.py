"""Schema validation for DeviceType."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

from jsonschema import validate, FormatChecker
from slugify import slugify

from dcim.models import Manufacturer, DeviceType

from netmapper import utils


def get_schema():
    """Return the JSON schema to validate DeviceType data."""
    return {
        "type": "object",
        "properties": {
            "manufacturer_id": {
                "type": "integer",
                "enum": list(Manufacturer.objects.all().values_list("id", flat=True)),
            },
            "model": {
                "type": "string",
            },
            "description": {
                "type": "string",
            },
        },
    }


def get_schema_create():
    """Return the JSON schema to validate new DeviceType objects."""
    schema = get_schema()
    schema["required"] = [
        "manufacturer_id",
        "model",
    ]
    return schema


def create(**kwargs):
    """Create a DeviceType."""
    kwargs = utils.delete_empty_keys(kwargs)
    validate(kwargs, get_schema_create(), format_checker=FormatChecker())
    kwargs["slug"] = kwargs.get("slug") or slugify(kwargs.get("model"))

    existing_obj = get(
        model=kwargs.get("model"),
        manufacturer_id=kwargs.get("manufacturer_id"),
        slug=kwargs.get("slug"),
        legacy_slug=slugify(kwargs.get("model")),
    )
    if existing_obj:
        return existing_obj

    obj = utils.object_create(DeviceType, **kwargs)
    return obj


def get(model=None, manufacturer_id=None, slug=None, legacy_slug=None):
    """Return a DeviceType."""
    if manufacturer_id is None:
        raise ValueError("manufacturer_id is required")

    if model is not None:
        obj = utils.object_get_or_none(
            DeviceType, model=model, manufacturer_id=manufacturer_id
        )
        if obj:
            return obj

    for current_slug in [slug, legacy_slug]:
        if not current_slug:
            continue
        obj = utils.object_get_or_none(
            DeviceType, slug=current_slug, manufacturer_id=manufacturer_id
        )
        if obj:
            return obj

    return None


def get_list(**kwargs):
    """Get a list of DeviceType objects."""
    validate(kwargs, get_schema(), format_checker=FormatChecker())
    result = utils.object_list(DeviceType, **kwargs)
    return result
