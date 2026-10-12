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
Unit test suite verifying the Dogma Mathematical Engine (dogma.py):
- Stacking penalty factors
- Layer resistance calculations with stacking penalties and exemptions
- EHP calculations (omni and lowest-resist)
- Capacitor simulation (stable equilibrium and unstable discharge integration)
- Mobility, agility, inertia, align time, and propulsion mechanics
- CPU and Powergrid resources and engineering upgrades
"""
from __future__ import annotations

import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_TESTS_DIR)
_APP_ROOT = os.path.dirname(_TOOLS_DIR)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from subsystems.fitting.dogma import (
    stacking_penalty_factor,
    calculate_resistances,
    calculate_layer_ehp,
    calculate_total_ehp,
    simulate_capacitor,
    calculate_mobility,
    calculate_resources,
)


class TestDogmaMathematicalEngine(unittest.TestCase):
    """Comprehensive test suite for Dogma mathematical formulas."""

    def test_stacking_penalty_factors(self) -> None:
        """Verifies standard EVE Online stacking penalty curve: S(n) = exp(- (n-1)^2 / 7.1289)."""
        # index 0 and 1 should return 1.0
        self.assertAlmostEqual(stacking_penalty_factor(0), 1.0, places=4)
        self.assertAlmostEqual(stacking_penalty_factor(1), 1.0, places=4)

        # index 2: ~0.8691
        self.assertAlmostEqual(stacking_penalty_factor(2), 0.8691, places=3)

        # index 3: ~0.5706
        self.assertAlmostEqual(stacking_penalty_factor(3), 0.5706, places=3)

        # index 4: ~0.2830
        self.assertAlmostEqual(stacking_penalty_factor(4), 0.2830, places=3)

        # index 5: ~0.1060
        self.assertAlmostEqual(stacking_penalty_factor(5), 0.1060, places=3)

        # index 6: ~0.0300
        self.assertAlmostEqual(stacking_penalty_factor(6), 0.0300, places=3)

        # Monotonically decreasing
        for i in range(1, 10):
            self.assertGreaterEqual(stacking_penalty_factor(i), stacking_penalty_factor(i + 1))

    def test_resistance_stacking_with_membranes_and_dc2(self) -> None:
        """
        Tests resistance stacking with Multispectrum Energized Membrane II,
        multiple membranes, and Damage Control II (exempt).
        """
        base_armor = {"em": 0.50, "thermal": 0.35, "kinetic": 0.25, "explosive": 0.10}

        # Membrane II: 20% all armor resists (stacking penalized)
        mem1 = {
            "name": "Multispectrum Energized Membrane II",
            "layer": "armor",
            "bonus": 0.20,
            "stacking_penalized": True,
            "stacking_group": "armor_resist",
        }
        mem2 = {
            "name": "Multispectrum Energized Membrane II",
            "layer": "armor",
            "bonus": 0.20,
            "stacking_penalized": True,
            "stacking_group": "armor_resist",
        }
        # Damage Control II: 15% armor resist (unpenalized)
        dc2 = {
            "name": "Damage Control II",
            "layer": "armor",
            "bonus": 0.15,
            "stacking_penalized": False,
        }

        # 1. Single membrane: effective bonus = 0.20
        res_single = calculate_resistances(base_armor, [mem1], "armor")
        base_em_res = 1.0 - 0.50
        expected_em_single = 1.0 - (base_em_res * (1.0 - 0.20))
        self.assertAlmostEqual(res_single["em"], expected_em_single, places=5)

        # 2. Two membranes: 1st bonus 0.20, 2nd bonus 0.20 * 0.86911998 = ~0.173824
        res_double = calculate_resistances(base_armor, [mem1, mem2], "armor")
        p2 = stacking_penalty_factor(2)
        expected_em_double = 1.0 - (base_em_res * (1.0 - 0.20) * (1.0 - (0.20 * p2)))
        self.assertAlmostEqual(res_double["em"], expected_em_double, places=5)

        # 3. Two membranes + DC2:
        # DC2 applies without penalty: (1.0 - 0.15)
        res_all = calculate_resistances(base_armor, [mem1, mem2, dc2], "armor")
        expected_em_all = 1.0 - (base_em_res * (1.0 - 0.15) * (1.0 - 0.20) * (1.0 - (0.20 * p2)))
        self.assertAlmostEqual(res_all["em"], expected_em_all, places=5)

    def test_layer_and_total_ehp(self) -> None:
        """Tests omni layer EHP and overall total EHP."""
        hp = 1000.0
        resists = {"em": 0.50, "thermal": 0.50, "kinetic": 0.50, "explosive": 0.50}
        # Omni resonance is 0.50, so EHP = 1000 / 0.50 = 2000
        self.assertAlmostEqual(calculate_layer_ehp(hp, resists), 2000.0, places=2)

        # Total EHP with 3 layers
        shield_res = {"em": 0.0, "thermal": 0.20, "kinetic": 0.40, "explosive": 0.50}
        armor_res = {"em": 0.50, "thermal": 0.35, "kinetic": 0.25, "explosive": 0.10}
        hull_res = {"em": 0.33, "thermal": 0.33, "kinetic": 0.33, "explosive": 0.33}

        layers = {
            "shield": (1000.0, shield_res),
            "armor": (1500.0, armor_res),
            "hull": (1200.0, hull_res),
        }
        omni_ehp, lowest_ehp = calculate_total_ehp(layers)
        self.assertGreater(omni_ehp, 3700.0)
        self.assertGreater(lowest_ehp, 0.0)
        # Lowest resist EHP in this profile is thermal (~5348.74)
        self.assertAlmostEqual(lowest_ehp, 5348.74, places=1)
        self.assertAlmostEqual(omni_ehp, 5313.21, places=1)

    def test_capacitor_simulation_stable(self) -> None:
        """Tests capacitor simulation for a stable fit."""
        # 1000 GJ capacity, 200s recharge
        # Peak recharge = 2.5 * 1000 / 200 = 12.5 GJ/s
        # Module drain: 10 GJ / 5s = 2.0 GJ/s
        # Drain <= Peak Recharge -> Cap Stable
        modules = [
            {"name": "Small Armor Repairer II", "cap_need": 10.0, "duration": 5.0, "is_active": True}
        ]
        result = simulate_capacitor(1000.0, 200.0, modules)

        self.assertTrue(result["is_stable"])
        self.assertAlmostEqual(result["peak_recharge_rate"], 12.5, places=2)
        self.assertAlmostEqual(result["continuous_drain"], 2.0, places=2)
        self.assertAlmostEqual(result["delta"], 10.5, places=2)
        self.assertIsNone(result["depletion_time_sec"])
        self.assertGreater(result["equilibrium_pct"], 80.0)
        self.assertLessEqual(result["equilibrium_pct"], 100.0)

    def test_capacitor_simulation_unstable(self) -> None:
        """Tests capacitor simulation for an unstable fit with depletion time integration."""
        # 1000 GJ capacity, 200s recharge -> peak recharge = 12.5 GJ/s
        # Heavy drain: 100 GJ / 5s = 20.0 GJ/s > 12.5 GJ/s -> Unstable
        modules = [
            {"name": "Heavy Warp Disruptor", "cap_need": 100.0, "duration": 5.0, "is_active": True}
        ]
        result = simulate_capacitor(1000.0, 200.0, modules)

        self.assertFalse(result["is_stable"])
        self.assertEqual(result["equilibrium_pct"], 0.0)
        self.assertIsNotNone(result["depletion_time_sec"])
        # Depletion time should be between 60s and 120s
        self.assertGreater(result["depletion_time_sec"], 60.0)
        self.assertLess(result["depletion_time_sec"], 120.0)

    def test_mobility_and_align_time(self) -> None:
        """Tests ship agility, align time, max speed, and propulsion calculations."""
        base_speed = 200.0  # m/s
        base_mass = 1_000_000.0  # kg
        base_agility = 3.0

        # Base align time without modules: 1.386294 * 1e6 * 3.0 * 1e-6 = 4.158882 s
        mob_base = calculate_mobility(base_speed, base_mass, base_agility, [])
        self.assertAlmostEqual(mob_base["align_time"], 4.158882, places=3)
        self.assertEqual(mob_base["max_speed"], 200.0)

        # Add 1600mm plate (+500k kg mass) and Inertial Stabilizer II (inertia_multiplier = 0.80)
        modules = [
            {"name": "1600mm Rolled Tungsten Compact Plates", "mass_add": 500_000.0},
            {"name": "Inertial Stabilizers II", "inertia_multiplier": 0.80, "stacking_group": "agility"},
            {
                "name": "10MN Afterburner II",
                "is_propulsion": True,
                "is_active": True,
                "thrust": 15_000_000.0,
                "speed_factor": 1.35,
            },
        ]
        mob_modded = calculate_mobility(base_speed, base_mass, base_agility, modules)

        self.assertEqual(mob_modded["total_mass"], 1_500_000.0)
        self.assertAlmostEqual(mob_modded["inertia_multiplier"], 0.80, places=4)
        # Total agility: 3.0 * 0.80 = 2.40
        self.assertAlmostEqual(mob_modded["total_agility"], 2.40, places=4)
        # Align time: 1.386294 * 1.5e6 * 2.40 * 1e-6 = 4.990658 s
        self.assertAlmostEqual(mob_modded["align_time"], 4.990658, places=3)
        # Active Afterburner increases max speed
        self.assertGreater(mob_modded["max_speed"], base_speed)

    def test_calculate_resources_engineering(self) -> None:
        """Tests CPU and PG calculation with Co-Processors and Reactor Control Units."""
        base_cpu = 300.0
        base_pg = 800.0

        modules = [
            {"name": "Heavy Missile Launcher II", "cpu": 55.0, "pg": 110.0},
            {"name": "Co-Processor II", "cpu_multiplier": 1.10, "cpu": 0.0, "pg": 1.0},
            {"name": "Reactor Control Unit II", "pg_multiplier": 1.15, "cpu": 16.0, "pg": 0.0},
            {"name": "Micro Auxiliary Power Core I", "pg_flat": 50.0, "cpu": 12.0, "pg": 0.0},
        ]

        res = calculate_resources(base_cpu, base_pg, modules)

        self.assertAlmostEqual(res["cpu_used"], 83.0, places=2)
        self.assertAlmostEqual(res["pg_used"], 111.0, places=2)
        self.assertAlmostEqual(res["cpu_output"], 330.0, places=2)
        # PG: (800 + 50) * 1.15 = 977.5
        self.assertAlmostEqual(res["pg_output"], 977.5, places=2)
        self.assertTrue(res["cpu_ok"])
        self.assertTrue(res["pg_ok"])


if __name__ == "__main__":
    unittest.main()
