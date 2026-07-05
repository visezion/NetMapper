"""Sidebar navigation buttons."""
__author__ = "Andrea Dainese"
__contact__ = "andrea@adainese.it"
__copyright__ = "Copyright 2022, Andrea Dainese"
__license__ = "GPLv3"

from netbox.plugins import PluginMenuButton, PluginMenuItem, PluginMenu

credential_buttons = [
    PluginMenuButton(
        link="plugins:netmapper:credential_add",
        title="Add",
        icon_class="mdi mdi-plus-thick",
    ),
    PluginMenuButton(
        link="plugins:netmapper:credential_bulk_import",
        title="Import",
        icon_class="mdi mdi-upload",
    ),
]

snmpcredential_buttons = [
    PluginMenuButton(
        link="plugins:netmapper:snmpcredential_add",
        title="Add",
        icon_class="mdi mdi-plus-thick",
    ),
]

network_scan_buttons = [
    PluginMenuButton(
        link="plugins:netmapper:network_scan",
        title="Run",
        icon_class="mdi mdi-radar",
    ),
]

diagram_buttons = [
    PluginMenuButton(
        link="plugins:netmapper:diagram_add",
        title="Add",
        icon_class="mdi mdi-plus-thick",
    ),
]

discoverable_buttons = [
    PluginMenuButton(
        link="plugins:netmapper:discoverable_add",
        title="Add",
        icon_class="mdi mdi-plus-thick",
    ),
    PluginMenuButton(
        link="plugins:netmapper:discoverable_bulk_import",
        title="Import",
        icon_class="mdi mdi-upload",
    ),
]

menu_discovery = (
    PluginMenuItem(
        link="plugins:netmapper:credential_list",
        link_text="Credentials",
        buttons=credential_buttons,
        permissions=["netmapper.view_credential"],
    ),
    PluginMenuItem(
        link="plugins:netmapper:snmpcredential_list",
        link_text="SNMP Credentials",
        buttons=snmpcredential_buttons,
        permissions=["netmapper.view_snmpcredential"],
    ),
    PluginMenuItem(
        link="plugins:netmapper:network_scan",
        link_text="Network Scan",
        buttons=network_scan_buttons,
        permissions=["netmapper.change_discoverable"],
    ),
    PluginMenuItem(
        link="plugins:netmapper:discoverable_list",
        link_text="Discoverables",
        buttons=discoverable_buttons,
        permissions=["netmapper.view_discoverable"],
    ),
    PluginMenuItem(
        link="plugins:netmapper:discoverylog_list",
        link_text="Logs",
        permissions=["netmapper.view_discoverylog"],
    ),
)

menu_tables = (
    PluginMenuItem(
        link="plugins:netmapper:arptableentry_list",
        link_text="ARP Table",
        permissions=["netmapper.view_arptableentry"],
    ),
    PluginMenuItem(
        link="plugins:netmapper:macaddresstableentry_list",
        link_text="MAC Address Table",
        permissions=["netmapper.view_macaddresstableentry"],
    ),
    PluginMenuItem(
        link="plugins:netmapper:routetableentry_list",
        link_text="Routing Table",
        permissions=["netmapper.view_routetableentry"],
    ),
)

menu = PluginMenu(
    label="NetMapper",
    groups=(
        (
            "Diagrams",
            (
                PluginMenuItem(
                    link="plugins:netmapper:diagram_list",
                    link_text="Diagrams",
                    buttons=diagram_buttons,
                    permissions=["netmapper.view_diagram"],
                ),
            ),
        ),
        ("Discovery", menu_discovery),
        ("Tables", menu_tables),
    ),
)
