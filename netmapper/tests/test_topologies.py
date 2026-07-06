"""Tests for topology helper behavior."""

from django.test import SimpleTestCase

from netmapper.topologies import build_location_group_artifacts


class TopologyHelperTest(SimpleTestCase):
    """Validate lightweight topology grouping helpers."""

    def test_build_location_group_artifacts_creates_anchor_nodes(self):
        """Devices with the same location group should gain a shared anchor."""
        nodes = {
            1: {
                "id": 1,
                "label": "sw1",
                "location_group_key": "location:10",
                "location_group_type": "location",
                "location_group_label": "HQ / MDF",
            },
            2: {
                "id": 2,
                "label": "sw2",
                "location_group_key": "location:10",
                "location_group_type": "location",
                "location_group_label": "HQ / MDF",
            },
        }

        group_nodes, group_edges = build_location_group_artifacts(nodes)

        self.assertEqual(len(group_nodes), 1)
        self.assertEqual(group_nodes[0]["label"], "HQ / MDF")
        self.assertTrue(group_nodes[0]["group_anchor"])
        self.assertEqual(len(group_edges), 2)
        self.assertTrue(all(edge["hidden"] for edge in group_edges))
