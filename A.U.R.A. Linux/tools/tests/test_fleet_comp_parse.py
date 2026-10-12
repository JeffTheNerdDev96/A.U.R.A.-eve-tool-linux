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
"""Fleet composition paste parsing and role buckets."""
from __future__ import annotations

import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_TESTS_DIR)
_APP_ROOT = os.path.dirname(_TOOLS_DIR)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from subsystems.fleet_comp.analyzer import (
    FleetCompAnalyzer,
    parse_fleet_paste,
    compare_fleets,
    ROLE_LOGI,
    ROLE_T3C,
    ROLE_RECON,
    ROLE_COVERT,
    ROLE_TACKLE,
    ROLE_MAINLINE,
)


class TestFleetCompParse(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = FleetCompAnalyzer()

    def test_screenshot_space_list(self) -> None:
        parsed = parse_fleet_paste("osprey osprey loki loki oni")
        self.assertEqual(parsed["total_ships"], 5)
        self.assertEqual(parsed["unmatched"], 0)
        self.assertEqual(parsed["ship_counts"]["Osprey"], 2)
        self.assertEqual(parsed["ship_counts"]["Loki"], 2)
        self.assertEqual(parsed["ship_counts"]["Oneiros"], 1)
        self.assertEqual(self.analyzer.categorize_ship("Osprey"), ROLE_LOGI)
        self.assertEqual(self.analyzer.categorize_ship("Loki"), ROLE_T3C)
        self.assertEqual(self.analyzer.categorize_ship("Oneiros"), ROLE_LOGI)

    def test_recon_and_eas_bucket(self) -> None:
        parsed = parse_fleet_paste("curse pilgrim huginn hyena kitsune")
        self.assertEqual(parsed["total_ships"], 5)
        for hull in parsed["ship_counts"]:
            self.assertEqual(self.analyzer.categorize_ship(hull), ROLE_RECON)

    def test_covert_not_recon(self) -> None:
        parsed = parse_fleet_paste("helios purifier hound")
        self.assertEqual(parsed["total_ships"], 3)
        for hull in parsed["ship_counts"]:
            self.assertEqual(self.analyzer.categorize_ship(hull), ROLE_COVERT)

    def test_tab_dscan_no_double_count(self) -> None:
        parsed = parse_fleet_paste("PilotA\tIshtar\t24 km\nPilotB\tIshtar\t12 km")
        self.assertEqual(parsed["total_ships"], 2)
        self.assertEqual(parsed["ship_counts"]["Ishtar"], 2)

    def test_overview_type_id_not_quantity(self) -> None:
        blob = "\n".join([
            "11965    Pilgrim    Pilgrim    48 km",
            "605    Scout    Magnate    12 km",
            "12745    Occo's Garbage Truck    Occator    162 km",
            "47466    Praxis makes Perfect    Praxis    66 km",
            "11963    R4    Rapier    52 km",
            "628    [NFG] Rupter-0    Arbitrator    -",
        ])
        parsed = parse_fleet_paste(blob)
        self.assertEqual(parsed["unmatched"], 0)
        self.assertEqual(parsed["ship_counts"].get("Pilgrim"), 1)
        self.assertEqual(parsed["ship_counts"].get("Magnate"), 1)
        self.assertEqual(parsed["ship_counts"].get("Occator"), 1)
        self.assertEqual(parsed["ship_counts"].get("Praxis"), 1)
        self.assertEqual(parsed["ship_counts"].get("Rapier"), 1)
        self.assertEqual(parsed["ship_counts"].get("Arbitrator"), 1)
        self.assertEqual(parsed["total_ships"], 6)
        self.assertEqual(self.analyzer.categorize_ship("Pilgrim"), ROLE_RECON)
        self.assertEqual(self.analyzer.categorize_ship("Rapier"), ROLE_RECON)

    def test_tab_overview_four_columns(self) -> None:
        parsed = parse_fleet_paste("11965\tPilgrim\tPilgrim\t48 km\n605\tScout\tMagnate\t12 km")
        self.assertEqual(parsed["total_ships"], 2)
        self.assertEqual(parsed["ship_counts"]["Pilgrim"], 1)
        self.assertEqual(parsed["ship_counts"]["Magnate"], 1)

    def test_quantities(self) -> None:
        parsed = parse_fleet_paste("8 Muninn\n15x Ishtar")
        self.assertEqual(parsed["ship_counts"]["Muninn"], 8)
        self.assertEqual(parsed["ship_counts"]["Ishtar"], 15)
        self.assertEqual(parsed["total_ships"], 23)

    def test_hostile_nicknames(self) -> None:
        parsed = parse_fleet_paste("wolf retri kiki")
        self.assertEqual(parsed["ship_counts"]["Wolf"], 1)
        self.assertEqual(parsed["ship_counts"]["Retribution"], 1)
        self.assertEqual(parsed["ship_counts"]["Kikimora"], 1)
        self.assertEqual(self.analyzer.categorize_ship("Wolf"), ROLE_TACKLE)
        self.assertEqual(self.analyzer.categorize_ship("Retribution"), ROLE_TACKLE)
        self.assertEqual(self.analyzer.categorize_ship("Kikimora"), ROLE_MAINLINE)

    def test_t1_ecm_stays_mainline(self) -> None:
        self.assertEqual(self.analyzer.categorize_ship("Blackbird"), ROLE_MAINLINE)

    def test_leshak_not_logistics(self) -> None:
        self.assertEqual(self.analyzer.categorize_ship("Leshak"), ROLE_MAINLINE)
        self.assertEqual(self.analyzer.categorize_ship("Ikitursa"), ROLE_MAINLINE)
        self.assertEqual(self.analyzer.categorize_ship("Osprey"), ROLE_LOGI)
        self.assertEqual(self.analyzer.categorize_ship("Oneiros"), ROLE_LOGI)
        self.assertEqual(self.analyzer.categorize_ship("Nestor"), ROLE_LOGI)
        self.assertEqual(self.analyzer.categorize_ship("Lif"), ROLE_LOGI)

    def test_compare_fleets_has_t3c_and_recon_rows(self) -> None:
        rows = compare_fleets({"Loki": 2, "Osprey": 1}, {"Curse": 1, "Helios": 1})
        keys = [row["key"] for row in rows]
        self.assertEqual(keys, ["logi", "tackle", "t3c", "mainline", "recon", "covert"])
        by_key = {row["key"]: row for row in rows}
        self.assertEqual(by_key["t3c"]["friendly_n"], 2)
        self.assertEqual(by_key["recon"]["enemy_n"], 1)
        self.assertEqual(by_key["covert"]["enemy_n"], 1)
        self.assertEqual(by_key["logi"]["friendly_n"], 1)


if __name__ == "__main__":
    unittest.main()
