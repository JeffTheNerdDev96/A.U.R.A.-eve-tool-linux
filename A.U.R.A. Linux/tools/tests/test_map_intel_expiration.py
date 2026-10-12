# -*- coding: utf-8 -*-
# ==============================================================================
# Adaptive Underworld Recon Array (A.U.R.A.)
# Copyright (C) 2026 JeffTheNerdDev96
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==============================================================================
"""
Automated unit tests verifying that intel feed effects added to the tactical
stargate map are cleared within 15 minutes (900 seconds) of ingestion.
"""
import os
import sys
import time
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_TESTS_DIR)
_APP_ROOT = os.path.dirname(_TOOLS_DIR)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from bootstrap import configure_qt_paths
configure_qt_paths()

from PyQt6.QtWidgets import QApplication
from core.event_bus import get_event_bus
from core.events import IntelStaleExpiredEvent
from subsystems.map import get_eve_map
from ui.tabs.map_tab import MapTabWidget, INTEL_TTL_SEC


class TestMapIntelExpiration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["A.U.R.A_Test", "-platform", "offscreen"])
        cls.eve_map = get_eve_map()

    def setUp(self):
        self.map_tab = MapTabWidget(eve_map=self.eve_map)
        # Center map on Jita (30000142)
        jita_rec = self.eve_map.resolve_system_name("Jita")
        self.assertIsNotNone(jita_rec)
        self.jita_id = int(jita_rec["id"])
        self.map_tab.set_location("Jita", self.jita_id)

    def tearDown(self):
        self.map_tab.unsubscribe_events()
        self.map_tab.deleteLater()

    def test_intel_add_effects_applied(self):
        """Verify intel effects (star backdrop, threat ring, label color) are applied."""
        now = time.time()
        self.map_tab.note_intel({
            "system": "Jita",
            "threat_level": "CRITICAL",
            "clean_msg": "Hostile dreadnought fleet lit cyno",
            "ingested_at": now,
        })

        node = self.map_tab._node_items.get(self.jita_id)
        self.assertIsNotNone(node)
        # Verify star item is visible
        self.assertIsNotNone(node._star_item)
        self.assertTrue(node._star_item.isVisible())
        # Verify intel is tracked
        self.assertIn("jita", self.map_tab._intel_by_system)
        self.assertEqual(self.map_tab._intel_by_system["jita"]["ts"], now)

    def test_intel_cleared_after_15_minutes_via_prune(self):
        """Verify intel effects are pruned and cleared after 15 minutes (900 seconds)."""
        now = time.time()
        self.map_tab.note_intel({
            "system": "Jita",
            "threat_level": "CRITICAL",
            "clean_msg": "Hostile dreadnought fleet lit cyno",
            "ingested_at": now,
        })
        node = self.map_tab._node_items.get(self.jita_id)
        self.assertIsNotNone(node)
        self.assertTrue(node._star_item.isVisible())

        # At now + 600s (10 min), report is still active
        pruned_10m = self.map_tab._prune_intel(current_time=now + 600.0)
        self.assertEqual(pruned_10m, [])
        self.assertIn("jita", self.map_tab._intel_by_system)

        # At now + 901s (> 15 min), report must be pruned
        pruned_15m = self.map_tab._prune_intel(current_time=now + 901.0)
        self.assertEqual(pruned_15m, ["jita"])
        self.assertNotIn("jita", self.map_tab._intel_by_system)

        # Rebuilding graph clears the star backdrop
        self.map_tab._rebuild_graph(full_layout=False, fit_view=False)
        updated_node = self.map_tab._node_items.get(self.jita_id)
        self.assertIsNotNone(updated_node)
        self.assertTrue(updated_node._star_item is None or not updated_node._star_item.isVisible())

    def test_intel_jit_ttl_guard(self):
        """Verify _intel_for_id purges stale entries on real-time lookup."""
        old_time = time.time() - (INTEL_TTL_SEC + 5.0)
        self.map_tab._intel_by_system["jita"] = {
            "level": "HIGH",
            "msg": "Hostiles spotted",
            "ts": old_time,
            "name": "Jita",
        }

        # _intel_for_id should identify it as expired, purge it, and return None
        intel = self.map_tab._intel_for_id(self.jita_id)
        self.assertIsNone(intel)
        self.assertNotIn("jita", self.map_tab._intel_by_system)

    def test_event_bus_stale_expired_event_clears_map(self):
        """Verify IntelStaleExpiredEvent clears intel effects from the map."""
        self.map_tab.note_intel({
            "system": "Jita",
            "threat_level": "HIGH",
            "clean_msg": "Hostile fleet in gate",
            "ingested_at": time.time(),
        })
        self.assertIn("jita", self.map_tab._intel_by_system)

        # Publish IntelStaleExpiredEvent
        bus = get_event_bus()
        bus.publish(IntelStaleExpiredEvent(system="Jita", expired_report_ids=["jita"]))

        # Jita should be cleared from map tracking
        self.assertNotIn("jita", self.map_tab._intel_by_system)
        node = self.map_tab._node_items.get(self.jita_id)
        self.assertIsNotNone(node)
        self.assertTrue(node._star_item is None or not node._star_item.isVisible())

    def test_route_view_without_origin_clears_intel(self):
        """Verify intel clears even when origin_id is None if route nodes are displayed."""
        unlocated_map_tab = MapTabWidget(eve_map=self.eve_map)
        try:
            self.assertIsNone(unlocated_map_tab._origin_id)
            # Plan route between Jita and Perimeter
            route = unlocated_map_tab.map_subsystem.plan_route("Jita", "Perimeter")
            self.assertIsNotNone(route)
            unlocated_map_tab._apply_route(route)
            self.assertTrue(bool(unlocated_map_tab._route_node_ids))

            now = time.time()
            unlocated_map_tab.note_intel({
                "system": "Perimeter",
                "threat_level": "MEDIUM",
                "clean_msg": "Sabre bubble on Jita gate",
                "ingested_at": now,
            })
            self.assertIn("perimeter", unlocated_map_tab._intel_by_system)

            # Prune at now + 905s
            stale = unlocated_map_tab._prune_intel(current_time=now + 905.0)
            self.assertEqual(stale, ["perimeter"])
            self.assertNotIn("perimeter", unlocated_map_tab._intel_by_system)

            # Rebuild graph to verify no exception when origin_id is None
            unlocated_map_tab._rebuild_graph(full_layout=False, fit_view=False)
        finally:
            unlocated_map_tab.unsubscribe_events()
            unlocated_map_tab.deleteLater()

    def test_clear_system_intel_method(self):
        """Verify clear_system_intel() removes intel effects on demand."""
        self.map_tab.note_intel({
            "system": "Jita",
            "threat_level": "CRITICAL",
            "clean_msg": "Hostiles on 4-4 station",
            "ingested_at": time.time(),
        })
        self.assertIn("jita", self.map_tab._intel_by_system)

        cleared = self.map_tab.clear_system_intel("Jita")
        self.assertTrue(cleared)
        self.assertNotIn("jita", self.map_tab._intel_by_system)
        node = self.map_tab._node_items.get(self.jita_id)
        self.assertTrue(node._star_item is None or not node._star_item.isVisible())


if __name__ == "__main__":
    unittest.main()
