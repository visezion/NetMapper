"""Regression tests for plugin URL naming compatibility."""

from django.test import SimpleTestCase
from django.urls import reverse


class PluginUrlCompatibilityTest(SimpleTestCase):
    """Ensure both NetBox-style and legacy route names reverse cleanly."""

    def test_snmpcredential_list_aliases_share_the_same_path(self):
        """The list view must support the hyphenated name expected by NetBox."""
        self.assertEqual(
            reverse("plugins:netmapper:snmpcredential-list"),
            reverse("plugins:netmapper:snmpcredential_list"),
        )

    def test_snmpcredential_named_routes_keep_backward_compatibility(self):
        """Hyphenated and underscored SNMP credential route names should match."""
        route_pairs = [
            ("snmpcredential-add", "snmpcredential_add"),
            ("snmpcredential-edit", "snmpcredential_edit"),
            ("snmpcredential-delete", "snmpcredential_delete"),
            ("snmpcredential-test", "snmpcredential_test"),
            ("snmpcredential-changelog", "snmpcredential_changelog"),
        ]

        for hyphenated_name, underscored_name in route_pairs:
            with self.subTest(route=hyphenated_name):
                self.assertEqual(
                    reverse(f"plugins:netmapper:{hyphenated_name}", kwargs={"pk": 1})
                    if "add" not in hyphenated_name
                    else reverse(f"plugins:netmapper:{hyphenated_name}"),
                    reverse(f"plugins:netmapper:{underscored_name}", kwargs={"pk": 1})
                    if "add" not in underscored_name
                    else reverse(f"plugins:netmapper:{underscored_name}"),
                )
