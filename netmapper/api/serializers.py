"""Serializers, called by API Views for add/ediit actions."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

from rest_framework import serializers

from netbox.api.serializers import NetBoxModelSerializer

from netmapper.models import (
    Credential,
    Discoverable,
    DiscoveryLog,
    RouteTableEntry,
    ArpTableEntry,
    MacAddressTableEntry,
    Diagram,
)


class ArpTableEntrySerializer(NetBoxModelSerializer):
    """Serializer to validate ArpTableEntry data."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netmapper-api:arptableentry-detail"
    )

    class Meta:
        """Serializer metadata."""

        model = ArpTableEntry
        fields = "__all__"
        brief_fields = ("id", "url", "display", "ip_address", "mac_address")


class CredentialSerializer(NetBoxModelSerializer):
    """Serializer to validate Credential data."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netmapper-api:credential-detail"
    )
    discoverables_count = serializers.IntegerField(read_only=True)

    class Meta:
        """Serializer metadata."""

        model = Credential
        fields = "__all__"
        brief_fields = ("id", "url", "display", "name")


class DiagramSerializer(NetBoxModelSerializer):
    """Serializer to validate Diagram data."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netmapper-api:diagram-detail"
    )
    discoverables_count = serializers.IntegerField(read_only=True)

    class Meta:
        """Serializer metadata."""

        model = Diagram
        fields = "__all__"
        brief_fields = ("id", "url", "display", "name", "mode")


class DiscoverableSerializer(NetBoxModelSerializer):
    """Serializer to validate Discoverable data."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netmapper-api:discoverable-detail"
    )

    class Meta:
        """Serializer metadata."""

        model = Discoverable
        fields = "__all__"
        brief_fields = ("id", "url", "display", "address", "mode")


class DiscoveryLogSerializer(NetBoxModelSerializer):
    """Serializer to validate DiscoveryLog data."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netmapper-api:discoverylog-detail"
    )

    class Meta:
        """Serializer metadata."""

        model = DiscoveryLog
        fields = "__all__"
        brief_fields = ("id", "url", "display", "command", "template")


class MacAddressTableEntrySerializer(NetBoxModelSerializer):
    """Serializer to validate MacAddressTableEntry data."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netmapper-api:macaddresstableentry-detail"
    )

    class Meta:
        """Serializer metadata."""

        model = MacAddressTableEntry
        fields = "__all__"
        brief_fields = ("id", "url", "display", "mac_address", "vvid")


class RouteTableEntrySerializer(NetBoxModelSerializer):
    """Serializer to validate RouteTableEntry data."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:netmapper-api:routetableentry-detail"
    )

    class Meta:
        """Serializer metadata."""

        model = RouteTableEntry
        fields = "__all__"
        brief_fields = ("id", "url", "display", "destination", "protocol")
