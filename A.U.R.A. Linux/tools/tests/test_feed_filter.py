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
Automated unit test suite verifying Live Intel Radar feed filter screening
on newly ingested entries as well as existing entries.
"""
import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_TESTS_DIR)
_APP_ROOT = os.path.dirname(_TOOLS_DIR)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from bootstrap import configure_qt_paths
configure_qt_paths()

from PyQt6.QtWidgets import QApplication
from ui import MainWindow


def test_feed_filter_new_entries():
    app = QApplication.instance() or QApplication(["A.U.R.A_Test", "-platform", "offscreen"])
    window = MainWindow()

    print("[TEST] 1. Testing Critical Only filter on newly ingested low threat...")
    window.threat_filter_combo.setCurrentText("Critical Only")

    low_ping = {
        "system": "Jita",
        "threat_level": "LOW",
        "status_flags": [],
        "clean_msg": "Scout > Jita gate clear",
        "time_str": "12:00:00",
    }
    window._handle_live_intel_line(low_ping)
    item_low = window.intel_list.item(0)
    assert item_low.isHidden() is True, "Low threat should be hidden under Critical Only"

    print("[TEST] 2. Testing Critical Only filter on newly ingested critical threat...")
    crit_ping = {
        "system": "Jita",
        "threat_level": "CRITICAL",
        "status_flags": ["CYNO SPOTTED"],
        "clean_msg": "Scout > Jita hostile cyno lit",
        "time_str": "12:00:05",
    }
    window._handle_live_intel_line(crit_ping)
    item_crit = window.intel_list.item(0)
    assert item_crit.isHidden() is False, "Critical threat should be visible under Critical Only"

    print("[TEST] 3. Testing Hide System Clears on newly ingested clear...")
    window.threat_filter_combo.setCurrentText("All Threats")
    window.hide_clears_cb.setChecked(True)

    clear_ping = {
        "system": "Amarr",
        "threat_level": "CLEAR",
        "status_flags": ["SYSTEM CLEAR"],
        "clean_msg": "Scout > Amarr clr",
        "time_str": "12:00:10",
    }
    window._handle_live_intel_line(clear_ping)
    item_clear = window.intel_list.item(0)
    assert item_clear.isHidden() is True, "Clear ping should be hidden when hide_clears_cb is checked"

    print("[TEST] 4. Testing Medium+ filter...")
    window.hide_clears_cb.setChecked(False)
    window.threat_filter_combo.setCurrentText("Medium+ Threats")

    med_ping = {
        "system": "Dodixie",
        "threat_level": "MEDIUM",
        "status_flags": [],
        "clean_msg": "Scout > Dodixie +3 hostiles",
        "time_str": "12:00:15",
    }
    window._handle_live_intel_line(med_ping)
    item_med = window.intel_list.item(0)
    assert item_med.isHidden() is False, "Medium threat should be visible under Medium+ Threats"

    print("[TEST] 5. Testing filter toggle retroactivity on existing entries...")
    window.threat_filter_combo.setCurrentText("Critical Only")
    assert item_med.isHidden() is True, "Medium threat should now be hidden under Critical Only"
    assert item_crit.isHidden() is False, "Critical threat should remain visible under Critical Only"

    window.close()
    print("[SUCCESS] ALL FEED FILTER SCREENING TESTS PASSED!")
    return True


if __name__ == "__main__":
    if not test_feed_filter_new_entries():
        sys.exit(1)
    sys.exit(0)
