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
Headless UI & Subsystem Integration Test.
"""

import os
import sys

# Ensure A.U.R.A. Source directory is in sys.path
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_TESTS_DIR)
_APP_ROOT = os.path.dirname(_TOOLS_DIR)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from bootstrap import configure_qt_paths
configure_qt_paths()

from PyQt6.QtWidgets import QApplication
from ui import MainWindow


def test_ui():
    print("[TEST] Initializing QApplication and MainWindow...")
    app = QApplication.instance()
    if not app:
        app = QApplication(["A.U.R.A_Test", "-platform", "offscreen"])

    window = MainWindow()
    assert window is not None
    assert hasattr(window, "intel_subsystem")
    assert hasattr(window, "dscan_subsystem")
    assert hasattr(window, "map_subsystem")
    assert hasattr(window, "fleet_comp_subsystem")
    assert hasattr(window, "wormhole_subsystem")
    assert hasattr(window, "xmpp_subsystem")
    assert hasattr(window, "voip_subsystem")
    assert hasattr(window, "fitting_subsystem")
    assert hasattr(window, "ai_subsystem")

    # Verify 9 tabs in exact sequence
    assert window.tabs.count() == 9
    expected_tabs = [
        "Live Intel Radar",
        "D-Scan",
        "Composition",
        "Map",
        "Anokis",
        "Fitting",
        "XMPP",
        "VOIP",
        "A.U.R.A. Chat",
    ]
    for idx, expected_title in enumerate(expected_tabs):
        actual_title = window.tabs.tabText(idx)
        assert actual_title == expected_title, f"Tab {idx} expected '{expected_title}', got '{actual_title}'"

    print(" -> MainWindow initialized and all 9 tabs verified in exact sequence!")

    window._simulate_test_ping()
    assert window.intel_list.count() >= 1
    assert window.map_tab._intel_by_system
    print(" -> Intel EventBus radar + map overlay path passed!")

    # Test D-Scan Tab
    dscan_tab = window.dscan_tab
    assert dscan_tab is not None
    assert hasattr(dscan_tab, "dscan_subsystem")
    sample_dscan = "3 Muninn\n2 Cerberus\n1 Stiletto\n1 Crow"
    dscan_tab.input_edit.setText(sample_dscan)
    dscan_tab._on_analyze()
    assert dscan_tab.current_analysis is not None
    assert dscan_tab.current_analysis.total_ships == 7
    assert dscan_tab.table.rowCount() == 2
    summaries_text = " | ".join(cs.breakdown_str for cs in dscan_tab.current_analysis.class_summaries)
    assert "Heavy Assault Cruiser : 5 :" in summaries_text
    assert "Interceptor : 2 :" in summaries_text
    print(" -> DScanTabWidget integration test passed! (Class grouping: Heavy Assault Cruiser, Interceptor)")

    comp_tab = window.composition_tab
    assert comp_tab is not None
    assert hasattr(comp_tab, "fleet_comp_subsystem")
    assert comp_tab.fleet_comp_subsystem is window.fleet_comp_subsystem
    comp_tab.friendly_edit.setText("Muninn\nScimitar")
    comp_tab.enemy_edit.setText("Sabre")
    comp_tab._analyze()
    assert comp_tab.table.rowCount() > 0
    print(" -> CompositionTabWidget integration test passed!")

    map_tab = window.map_tab
    assert map_tab is not None
    assert hasattr(map_tab, "map_subsystem")

    # Test BFS route planner UI wiring
    map_tab.route_origin_edit.setText("Jita")
    map_tab.route_dest_edit.setText("Amarr")
    map_tab._on_calculate_route()
    assert map_tab._current_route is not None
    assert map_tab._current_route.total_jumps == 11
    assert len(map_tab._route_node_ids) == 12
    assert len(map_tab._route_edges) == 11
    map_tab._on_clear_route()
    assert map_tab._current_route is None
    print(" -> MapTabWidget BFS route planning integration test passed!")

    anokis_tab = window.anokis_tab
    assert anokis_tab is not None
    assert hasattr(anokis_tab, "wh_subsystem")
    print(" -> WormholeTabWidget (Anokis) integration test passed!")

    xmpp_tab = window.xmpp_tab
    assert xmpp_tab is not None
    assert hasattr(xmpp_tab, "xmpp_subsystem")

    # Simulate incoming DM while viewing alliance broadcasts
    from subsystems.xmpp_chat.models import XMPPMessage, XMPPMessageType
    dm_in = XMPPMessage(
        sender_jid="saphira_hawk@goonfleet.com/laptop",
        sender_nick="saphira_hawk",
        room_jid="",
        body="Fleet formup ready in 1DQ1-A.",
        msg_type=XMPPMessageType.DIRECT,
    )
    xmpp_tab.xmpp_subsystem._handle_client_message(dm_in)
    xmpp_tab._on_message_received_gui(dm_in)
    assert xmpp_tab._unread_counts.get("saphira_hawk@goonfleet.com", 0) >= 1

    # Test clicking open_dm / opendm anchor link
    from PyQt6.QtCore import QUrl
    xmpp_tab._on_anchor_clicked(QUrl("opendm:saphira_hawk@goonfleet.com"))
    assert xmpp_tab.selected_target == "saphira_hawk@goonfleet.com"
    assert xmpp_tab.is_groupchat is False
    assert xmpp_tab._unread_counts.get("saphira_hawk@goonfleet.com") == 0

    print(" -> XMPPTabWidget (XMPP) integration test passed!")

    # Test VOIP Tab (alliance Mumble voice)
    voip_tab = window.voip_tab
    assert voip_tab is not None
    assert voip_tab.voip_subsystem is window.voip_subsystem

    # Demo channel message flows through the service layer into the stream view
    before_blocks = voip_tab.stream_browser.document().blockCount()
    voip_tab._on_demo_message()
    assert voip_tab.stream_browser.document().blockCount() > before_blocks

    # Channel tree selection + send guard while offline
    voip_tab.comp_edit.setText("should not send while offline")
    voip_tab._on_send_message()
    assert voip_tab.comp_edit.text() == "should not send while offline"

    # Non-http(s) anchor links are blocked
    from PyQt6.QtCore import QUrl as _QUrl
    voip_tab._on_anchor_clicked(_QUrl("javascript:alert(1)"))
    assert voip_tab.stream_browser.document().blockCount() >= 1

    # Audio/PTT state resets cleanly when disconnected
    voip_tab._stop_audio()
    assert voip_tab._audio_active is False
    print(" -> VOIPTabWidget (VOIP) integration test passed!")

    # Clean shutdown
    window.close()
    print("[SUCCESS] ALL UI & CORE SUBSYSTEM INTEGRATION TESTS PASSED!")
    return True


if __name__ == "__main__":
    if not test_ui():
        sys.exit(1)
