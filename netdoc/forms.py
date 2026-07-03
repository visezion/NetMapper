"""Forms, called by Views."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

from django import forms

from dcim.models import Site, DeviceRole, Device
from ipam.models import VRF
from virtualization.models import VirtualMachine

from utilities.forms import (
    BOOLEAN_WITH_BLANK_CHOICES,
    add_blank_choice,
)
from utilities.forms.widgets import APISelect
from utilities.forms.fields import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    CSVModelChoiceField,
)
from netbox.forms import (
    NetBoxModelForm,
    NetBoxModelFilterSetForm,
    NetBoxModelImportForm,
    NetBoxModelBulkEditForm,
)

from netdoc.models import (
    Credential,
    Diagram,
    Discoverable,
    DiscoveryLog,
    DiscoveryModeChoices,
    DiagramModeChoices,
)


def _coerce_nullable_boolean(value):
    """Convert a form choice into True, False, or None."""
    if value in (True, "True", "true", "1", 1):
        return True
    if value in (False, "False", "false", "0", 0):
        return False
    return None


def nullable_boolean_field(**kwargs):
    """Return a three-state boolean select compatible with current Django versions."""
    kwargs.setdefault("required", False)
    return forms.TypedChoiceField(
        choices=BOOLEAN_WITH_BLANK_CHOICES,
        coerce=_coerce_nullable_boolean,
        empty_value=None,
        **kwargs,
    )

#
# Credential forms
#


class CredentialForm(NetBoxModelForm):
    """Form used to add/edit Credential."""

    username = forms.CharField(required=False)

    class Meta:
        """Form metadata."""

        model = Credential
        fields = [
            "name",
            "username",
            "password",
            "enable_password",
            "verify_cert",
            "tags",
        ]
        widgets = {
            "password": forms.PasswordInput(
                render_value=True, attrs={"data-toggle": "password"}
            ),
            "enable_password": forms.PasswordInput(
                render_value=True, attrs={"data-toggle": "password"}
            ),
        }


class CredentialCSVForm(NetBoxModelImportForm):
    """Form used to add Credential objects via CSV import."""

    class Meta:
        """Form metadata."""

        model = Credential
        fields = ["name", "username", "password", "enable_password", "verify_cert"]


class CredentialBulkEditForm(NetBoxModelBulkEditForm):
    """Form used to bulk edit Credential objects."""

    username = forms.CharField(required=False)
    password = forms.CharField(required=False, widget=forms.PasswordInput)
    enable_password = forms.CharField(required=False, widget=forms.PasswordInput)

    model = Credential
    nullable_fields = ["username", "password", "enable_password", "verify_cert"]


#
# Diagram forms
#


class DiagramForm(NetBoxModelForm):
    """Form used to add/edit Diagram."""

    name = forms.CharField(required=True, strip=True)
    mode = forms.ChoiceField(choices=DiagramModeChoices, required=True)
    vrfs = DynamicModelMultipleChoiceField(
        queryset=VRF.objects.all(),
        required=False,
    )
    include_global_vrf = forms.BooleanField(
        required=False,
        initial=False,
        help_text="If set and no VRF is selected, Global only is included."
        + " If set and VRFs are selected, Global is included.",
    )
    sites = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        required=False,
    )
    device_roles = DynamicModelMultipleChoiceField(
        queryset=DeviceRole.objects.all(),
        required=False,
    )

    class Meta:
        """Form metadata."""

        model = Diagram
        fields = [
            "name",
            "mode",
            "device_roles",
            "sites",
            "vrfs",
            "include_global_vrf",
            "tags",
        ]

    def clean_name(self):
        """Reject blank names after trimming whitespace."""
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Name is required.")
        return name


#
# Discoverable views
#


class DiscoverableForm(NetBoxModelForm):
    """Form used to add/edit Discoverable."""

    address = forms.GenericIPAddressField()
    credential = forms.ModelChoiceField(
        queryset=Credential.objects.all(),
        required=True,
    )
    mode = forms.ChoiceField(choices=DiscoveryModeChoices, required=True)
    discoverable = forms.BooleanField(
        required=False,
        initial=True,
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        help_text="Site",
        required=True,
    )

    class Meta:
        """Form metadata."""

        model = Discoverable
        fields = [
            "address",
            "credential",
            "mode",
            "discoverable",
            "site",
            "tags",
        ]


class DiscoverableCSVForm(NetBoxModelImportForm):
    """Form used to add Discoverable objects via CSV import."""

    address = forms.GenericIPAddressField(
        help_text="Management IP address",
    )
    credential = CSVModelChoiceField(
        queryset=Credential.objects.all(),
        required=True,
        to_field_name="name",
        help_text="Assigned credential",
    )
    mode = forms.ChoiceField(
        choices=DiscoveryModeChoices,
        required=True,
        help_text="Discovery mode",
    )
    site = CSVModelChoiceField(
        queryset=Site.objects.all(),
        to_field_name="name",
        help_text="Site",
        required=True,
    )

    class Meta:
        """Form metadata."""

        model = Discoverable
        fields = ["address", "credential", "mode", "site"]


class DiscoverableBulkEditForm(NetBoxModelBulkEditForm):
    """Form used to bulk edit Discoverable objects."""

    credential = CSVModelChoiceField(
        queryset=Credential.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned credential",
    )
    mode = forms.ChoiceField(
        choices=add_blank_choice(DiscoveryModeChoices),
        required=False,
        initial="",
        widget=forms.Select(),
        help_text="Discovery mode",
    )
    discoverable = nullable_boolean_field(
        help_text="Is discoverable?",
    )
    site = forms.ModelChoiceField(
        queryset=Site.objects.all(),
        to_field_name="name",
        help_text="Site",
        required=False,
    )

    model = Discoverable
    nullable_fields = ["device"]


class DiscoverableListFilterForm(NetBoxModelFilterSetForm):
    """Form used to filter Discoverable using parameters. Used in DiscoverableListView."""

    model = Discoverable
    discoverable = nullable_boolean_field(
        label="Is discoverable?",
    )
    mode = forms.ChoiceField(
        choices=DiscoveryModeChoices,
        required=False,
        help_text="Discovery mode",
    )


class DiscoveryLogListFilterForm(NetBoxModelFilterSetForm):
    """Form used to filter DiscoveryLog using parameters. Used in DiscoveryLogListView."""

    model = DiscoveryLog
    discoverable__device = forms.ModelChoiceField(
        queryset=Device.objects.all(),
        to_field_name="id",
        required=False,
        widget=APISelect(api_url="/api/dcim/devices/"),
        label="Associated device",
    )
    discoverable__vm = forms.ModelChoiceField(
        queryset=VirtualMachine.objects.all(),
        to_field_name="id",
        required=False,
        widget=APISelect(api_url="/api/virtualization/virtual-machines/"),
        label="Associated VM",
    )
    configuration = nullable_boolean_field(
        label="Configuration output",
    )
    success = nullable_boolean_field(
        label="Completed successfully",
    )
    supported = nullable_boolean_field(
        label="Command is supported",
    )
    parsed = nullable_boolean_field(
        label="Parsed successfully",
    )
    ingested = nullable_boolean_field(
        label="Ingested successfully",
    )
