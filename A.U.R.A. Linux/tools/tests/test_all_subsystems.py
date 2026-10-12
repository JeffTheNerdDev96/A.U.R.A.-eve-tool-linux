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
Automated unit and integration tests for A.U.R.A. Subsystems:
- IntelSubsystem
- MapSubsystem
- FleetCompSubsystem
- FittingSubsystem
- WormholeSubsystem (Anokis)
- XMPPChatSubsystem
- VOIPMumbleSubsystem
- EventBus
"""

import os
import sys

# Ensure A.U.R.A. Source directory is in sys.path
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_TESTS_DIR)
_APP_ROOT = os.path.dirname(_TOOLS_DIR)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from version import VERSION
from core import get_event_bus
from core.events import (
    IntelReportEvent, XMPPBroadcastAlertEvent, XMPPMessageReceivedEvent,
    VOIPConnectionStateChangedEvent, VOIPChannelUpdatedEvent,
    VOIPTextMessageEvent, VOIPUserSpeakingEvent,
)
from subsystems.intel import IntelSubsystem, IntelReport, ThreatStatus, IntelParser
from subsystems.intel.monitor import decode_log_bytes
from subsystems.map import MapSubsystem
from subsystems.fleet_comp import FleetCompSubsystem
from subsystems.fitting import FittingSubsystem
from subsystems.wormhole import WormholeSubsystem, WormholeClass, CosmicSignature, SignatureGroup
from subsystems.xmpp_chat import (
    XMPPChatSubsystem, XMPPAccountConfig, XMPPBroadcastPriority,
    XMPPMessage, XMPPMessageType, XMPPMUCChannel,
    parse_broadcast_ping,
)
from subsystems.voip_mumble import (
    VOIPMumbleSubsystem, VOIPAccountConfig, VOIPConnectionState,
    VOIPChannel, VOIPUser,
)


def test_subsystems():
    print(f"[TEST] Version source data check: {VERSION}")
    assert VERSION == "v0.6.0-alpha.4", f"Expected v0.6.0-alpha.4 but got {VERSION}"

    # 1. EventBus Test
    print("[TEST] EventBus publishing & subscription check...")
    eb = get_event_bus()
    received_events = []

    def handle_event(evt):
        received_events.append(evt)

    eb.subscribe(IntelReportEvent, handle_event)
    test_intel_event = IntelReportEvent(
        system="1DQ1-A",
        pilots=["Hostile1"],
        ship_classes=["Sabre"],
        threat_level="CRITICAL",
        raw_line="Delve 1DQ1-A 50 Hostiles in Sprout",
        channel_name="Delve",
        reporter="Scout"
    )
    eb.publish(test_intel_event)
    assert len(received_events) == 1, "EventBus failed to dispatch to subscriber"
    assert received_events[0].system == "1DQ1-A"
    print(" -> EventBus passed!")

    # 2. Intel Subsystem & Decoder Tests
    print("[TEST] IntelSubsystem parsing, encoding resilience & threat scoring check...")
    
    # 2a. Test log encoding resilience
    raw_sample = "[ 2026.08.23 20:01:23 ] ScoutAlpha > 1DQ1-A +5 Loki Cynabal gate bubbled"
    assert decode_log_bytes(raw_sample.encode("utf-8")) == raw_sample
    assert decode_log_bytes(b"\xff\xfe" + raw_sample.encode("utf-16-le")) == raw_sample
    assert decode_log_bytes(raw_sample.encode("utf-16-le")) == raw_sample
    assert decode_log_bytes(b"\xef\xbb\xbf" + raw_sample.encode("utf-8")) == raw_sample
    assert decode_log_bytes(raw_sample.encode("utf-16-le")[:-1]) == raw_sample[:-1]

    # 2b. Test IntelParser full line parsing
    p = IntelParser.parse_single_line(raw_sample, "Delve.Intel")
    assert p is not None
    assert p["system"] == "1DQ1-A"
    assert p["speaker"] == "ScoutAlpha"
    assert p["time_str"] == "2026.08.23 20:01:23"
    assert p["clean_msg"] == "1DQ1-A +5 Loki Cynabal gate bubbled"
    assert "Loki" in p["ships"] and "Cynabal" in p["ships"]
    assert p["has_bubble"] is True
    assert p["est_count"] == 5
    assert p["threat_level"] == "MEDIUM"

    intel_sub = IntelSubsystem()
    assert intel_sub.initialize() is True
    assert intel_sub.start() is True

    parsed_reports = intel_sub.process_intel_line("1DQ1-A *CLR* 12:00:00")
    assert len(parsed_reports) >= 1
    assert isinstance(parsed_reports[0], IntelReport)
    assert parsed_reports[0].system == "1DQ1-A"
    assert parsed_reports[0].threat_level == ThreatStatus.CLEAR

    hostile_reports = intel_sub.process_intel_line("Jita +15 Tornado, Sabre, Loki")
    assert len(hostile_reports) >= 1
    assert hostile_reports[0].system.upper() == "JITA"
    assert hostile_reports[0].threat_level in (ThreatStatus.CRITICAL, ThreatStatus.HOSTILE, "HOSTILE", "CRITICAL", "HIGH")
    print(" -> IntelSubsystem & Decoder passed!")

    # 3. Map Subsystem Routing Test
    print("[TEST] MapSubsystem stargate BFS pathfinding check...")
    map_sub = MapSubsystem()
    assert map_sub.initialize() is True
    assert map_sub.start() is True

    route = map_sub.plan_route("Jita", "Amarr")
    assert route is not None
    assert route.total_jumps > 0
    assert route.start_system == "Jita"
    assert route.destination_system == "Amarr"
    assert route.path[0] == "Jita"
    assert route.path[-1] == "Amarr"
    print(f" -> MapSubsystem passed! Path ({route.total_jumps} jumps): {route.path[:2]} ... {route.path[-1]}")

    # 4. Fleet Comp Subsystem Test
    print("[TEST] FleetCompSubsystem role breakdown & doctrine counters check...")
    fleet_sub = FleetCompSubsystem()
    assert fleet_sub.initialize() is True
    assert fleet_sub.start() is True

    sample_dscan = """
    Scimitar	1234	25 km
    Basilisk	5678	30 km
    Muninn	9012	40 km
    Muninn	3456	42 km
    Cerberus	7890	45 km
    Sabre	1122	15 km
    Flycatcher	3344	18 km
    Falcon	5566	80 km
    Arazu	7788	75 km
    """
    analysis = fleet_sub.evaluate_fleet(sample_dscan)
    assert analysis.total_ships == 9
    assert analysis.logistics_count == 2
    assert analysis.mainline_dps_count == 3
    sample_fleet = "Pilot Alpha\tGuardian\tFleet Member\nPilot Beta\tZealot\tFleet Member\n"
    analysis_fleet = fleet_sub.evaluate_fleet(sample_fleet)
    assert analysis_fleet is not None
    assert analysis_fleet.total_ships == 2
    assert fleet_sub.stop() is True
    print(f" -> FleetCompSubsystem passed! Total ships: {analysis_fleet.total_ships}")

    # 4.5 D-Scan Subsystem Test
    print("[TEST] DScanSubsystem class breakdown & itemized quantities check...")
    from subsystems.dscan import DScanSubsystem
    dscan_sub = DScanSubsystem()
    assert dscan_sub.initialize() is True
    assert dscan_sub.start() is True

    sample_dscan_raw = """
    Muninn\t1234\t40 km
    Cerberus\t3456\t42 km
    Cerberus\t7890\t45 km
    Stiletto\t1122\t15 km
    Crow\t3344\t18 km
    """
    d_analysis = dscan_sub.parse_dscan(sample_dscan_raw)
    assert d_analysis.total_ships == 5
    assert len(d_analysis.class_summaries) == 2
    summaries = {cs.ship_class: cs for cs in d_analysis.class_summaries}
    assert "Heavy Assault Cruiser" in summaries
    assert summaries["Heavy Assault Cruiser"].total_count == 3
    assert "Cerberus x2" in summaries["Heavy Assault Cruiser"].breakdown_str
    assert "Muninn" in summaries["Heavy Assault Cruiser"].breakdown_str
    assert "Heavy Assault Cruiser : 3 :" in summaries["Heavy Assault Cruiser"].breakdown_str
    assert "Interceptor" in summaries
    assert summaries["Interceptor"].total_count == 2
    assert "Interceptor : 2 :" in summaries["Interceptor"].breakdown_str
    assert dscan_sub.stop() is True
    print(f" -> DScanSubsystem passed! Ships: {d_analysis.total_ships}, Classes: {len(d_analysis.class_summaries)}")

    # 5. Fitting Subsystem Test
    print("[TEST] FittingSubsystem EFT parser & Dogma calculation check...")
    fit_sub = FittingSubsystem()
    assert fit_sub.initialize() is True
    assert fit_sub.start() is True

    sample_eft = """[Rifter, Solo PvP]
Damage Control II
Small Armor Repairer II
200mm Rolled Tungsten Compact Armor Plate

1MN Afterburner II
Warp Scrambler II
Fleeting Compact Stasis Webifier

200mm AutoCannon II, Republic Fleet EMP S
200mm AutoCannon II, Republic Fleet EMP S
200mm AutoCannon II, Republic Fleet EMP S
[Empty High slot]

Small Trimark Armor Pump I
Small Trimark Armor Pump I
Small Projectile Burst Aerator I
"""
    parsed_fit = fit_sub.parse_eft(sample_eft)
    assert parsed_fit is not None
    assert parsed_fit.ship_name == "Rifter"
    assert parsed_fit.fit_name == "Solo PvP"
    assert parsed_fit.stats.get("ehp", 0) > 0

    # Hardpoint & Single-fit enforcement tests
    from subsystems.fitting.stats import validate_module_fit
    # 1. Hardpoint rejection (Rifter has 3 turret hardpoints)
    ok, reason = validate_module_fit("Rifter", ["200mm AutoCannon II", "200mm AutoCannon II", "200mm AutoCannon II"], "200mm AutoCannon II")
    assert not ok, "Expected 4th turret to be rejected on Rifter"

    # 2. Single-fit rejection (DCU)
    ok, reason = validate_module_fit("Rifter", ["Damage Control II"], "Damage Control II")
    assert not ok, "Expected 2nd DCU to be rejected"

    # 3. Single-fit rejection (AAR)
    ok, reason = validate_module_fit("Rifter", ["Small Ancillary Armor Repairer"], "Small Ancillary Armor Repairer")
    assert not ok, "Expected 2nd AAR to be rejected"

    # 4. Multi-fit permitted (Dual-Prop)
    ok, reason = validate_module_fit("Rifter", ["1MN Afterburner II"], "5MN Microwarpdrive II")
    assert ok, "Dual-Prop must be allowed"

    # 5. Multi-fit permitted (Dual-ASB)
    ok, reason = validate_module_fit("Cyclone", ["Medium Ancillary Shield Booster"], "Medium Ancillary Shield Booster")
    assert ok, "Dual-ASB must be allowed"

    # 6. EFT Parser drops invalid extra modules and populates warnings
    illegal_eft = """[Rifter, Illegal Fit]
Damage Control II
Damage Control II
Small Ancillary Armor Repairer
Small Ancillary Armor Repairer

200mm AutoCannon II
200mm AutoCannon II
200mm AutoCannon II
200mm AutoCannon II
"""
    illegal_parsed = fit_sub.parse_eft(illegal_eft)
    assert illegal_parsed is not None
    assert len(illegal_parsed.rejected_modules) >= 2
    assert len(illegal_parsed.validation_warnings) >= 2

    assert fit_sub.stop() is True
    print(f" -> FittingSubsystem passed! Fit: [{parsed_fit.ship_name}, {parsed_fit.fit_name}] EHP: {parsed_fit.stats.get('ehp', 0):.0f}, validation verified.")

    # 6. Wormhole Subsystem (Anokis) Test
    print("[TEST] WormholeSubsystem chain topology & timer decay check...")
    wh_sub = WormholeSubsystem()
    assert wh_sub.initialize() is True
    assert wh_sub.start() is True
    home_node = wh_sub.set_home_system("J100000", WormholeClass.C4)
    assert home_node.system_name == "J100000"
    assert home_node.system_class == WormholeClass.C4

    child_node = wh_sub.add_system("J200000", parent_system="J100000", wormhole_type="C247", system_class=WormholeClass.C3, lifetime_duration_hours=16.0)
    assert child_node is not None
    assert child_node.system_name == "J200000"

    sig = CosmicSignature(sig_id="ABC-123", group=SignatureGroup.RELIC, name="Ruins", signal_strength=100.0)
    assert wh_sub.add_or_update_signature("J200000", "ABC-123", sig) is True

    summary = wh_sub.get_chain_summary()
    assert summary["nodes_count"] == 2
    assert summary["connections_count"] == 1

    # Test link removal
    wh_sub.add_system("J300000", parent_system="J100000", wormhole_type="N432", system_class=WormholeClass.C5, lifetime_duration_hours=24.0)
    assert len(wh_sub.active_chain.nodes) == 3
    wh_sub.remove_system("J300000")
    assert len(wh_sub.active_chain.nodes) == 2

    # Test timer expiration and clearance
    conn = wh_sub.active_chain.connections[0]
    import time
    conn.expires_at = time.time() - 5.0
    eol, expired = wh_sub.update_connection_timers()
    assert len(expired) == 1
    cleared = wh_sub.clear_expired_connections()
    assert cleared == 1
    assert len(wh_sub.active_chain.connections) == 0

    assert wh_sub.stop() is True
    print(" -> WormholeSubsystem passed! Timers and connection removal verified.")

    # 7. XMPP Chat Subsystem Test
    print("[TEST] XMPPChatSubsystem ephemeral config & broadcast ping parsing check...")
    xmpp_sub = XMPPChatSubsystem()
    assert xmpp_sub.initialize() is True
    assert xmpp_sub.start() is True

    cfg = XMPPAccountConfig(
        jid="recon@goonfleet.com",
        password="test_ephemeral_password",
        host_override="xmpp.goonfleet.com",
        port=5222,
    )
    assert cfg.username == "recon"
    assert cfg.domain == "goonfleet.com"

    # Test broadcast ping extraction
    raw_ping = (
        "*** ALLIANCE BROADCAST ***\n"
        "STRATOP: Armor Timer in 1DQ1-A\n"
        "FC: Asher Elias\n"
        "DOCTRINE: Sacrilege / Guardian\n"
        "LOCATION: 1DQ1-A\n"
        "PAP: https://auth.goonfleet.com/pap/9988\n"
        "Formup now in staging!"
    )
    parsed_bcast = parse_broadcast_ping(raw_ping)
    assert parsed_bcast is not None
    assert parsed_bcast.staging_system == "1DQ1-A"
    assert parsed_bcast.target_system == "1DQ1-A"
    assert parsed_bcast.fc_name == "Asher Elias"
    assert parsed_bcast.priority == XMPPBroadcastPriority.STRATOP
    assert "Sacrilege" in parsed_bcast.doctrine_ships or "Guardian" in parsed_bcast.doctrine_ships

    # Test FC Name, Formup Location, and coord broadcast format from Elysium
    elysium_ping = (
        "FC Name: Rocko MonkeyBone\n"
        "Formup Location: C-J6MT\n"
        "PAP Type: Strategic\n"
        "Comms: Op 9 https://gnf.lt/vEALwCF.html\n"
        "Doctrine: Void Rays (MWD kikis) (Boosts > Logi > Kikis > Slasher, Hyena, Keres)\n\n"
        "~~~ This was a coord broadcast from sapphire_bloodbane to all at 2026-08-28 08:29:32.909586 EVE ~~~"
    )
    parsed_elysium = parse_broadcast_ping(elysium_ping)
    assert parsed_elysium is not None
    assert parsed_elysium.fc_name == "Rocko MonkeyBone"
    assert parsed_elysium.staging_system == "C-J6MT"
    assert parsed_elysium.target_system == "C-J6MT"
    assert parsed_elysium.priority == XMPPBroadcastPriority.STRATOP

    # Test variations (Forumup Location, Forumup, LOC, Staging System)
    loc_var_ping = (
        "*** ALLIANCE BROADCAST ***\n"
        "FC name: Valkyrie\n"
        "Forumup Location: Nol-M9\n"
        "DOCTRINE: Cerberus\n"
        "CTA MAX NUMBERS"
    )
    parsed_loc_var = parse_broadcast_ping(loc_var_ping)
    assert parsed_loc_var is not None
    assert parsed_loc_var.fc_name == "Valkyrie"
    assert parsed_loc_var.staging_system == "NOL-M9"
    assert parsed_loc_var.priority == XMPPBroadcastPriority.CTA

    # Test synthetic ping injection & event dispatch
    received_pings = []
    def on_xmpp_ping(evt):
        received_pings.append(evt)
    eb.subscribe(XMPPBroadcastAlertEvent, on_xmpp_ping)

    msg = xmpp_sub.inject_simulated_ping(target_system="1DQ1-A", doctrine="Tengu", fc="Asher Elias", body=raw_ping)
    assert msg.is_broadcast is True
    assert len(received_pings) >= 1
    assert received_pings[0].target_system == "1DQ1-A"

    # Test direct message handling and dynamic roster addition
    listener_received_messages = []
    eb.subscribe(XMPPMessageReceivedEvent, lambda evt: listener_received_messages.append(evt.message))

    dm_msg = XMPPMessage(
        sender_jid="saphira_hawk@goonfleet.com/resource",
        sender_nick="saphira_hawk",
        recipient_jid="jeff_helugo@goonfleet.com",
        room_jid="",
        body="Hello FC, reporting for fleet duty.",
        msg_type=XMPPMessageType.DIRECT,
    )
    xmpp_sub._handle_client_message(dm_msg)
    dms = xmpp_sub.get_direct_chats()
    assert len(dms) >= 1
    assert any("saphira_hawk" in c.jid for c in dms)
    assert len(listener_received_messages) == 1
    assert listener_received_messages[0].body == "Hello FC, reporting for fleet duty."

    # Test outgoing direct message symmetry in message history
    dm_reply = XMPPMessage(
        sender_jid="jeff_helugo@goonfleet.com/aura",
        sender_nick="jeff_helugo",
        recipient_jid="saphira_hawk@goonfleet.com",
        room_jid="",
        body="Welcome pilot, get into the Sacrilege fleet.",
        msg_type=XMPPMessageType.DIRECT,
    )
    xmpp_sub._handle_client_message(dm_reply)

    # Test symmetric message filtering for direct conversations
    dm_history = xmpp_sub.get_messages("saphira_hawk@goonfleet.com")
    assert len(dm_history) == 2
    assert dm_history[0].body == "Hello FC, reporting for fleet duty."
    assert dm_history[1].body == "Welcome pilot, get into the Sacrilege fleet."

    # Test directory discovery
    dir_rooms = [
        XMPPMUCChannel(room_jid="standing@conference.goonfleet.com", name="Standing Fleet", is_directory_room=True),
        XMPPMUCChannel(room_jid="miners@conference.goonfleet.com", name="Mining Operations", is_directory_room=True),
    ]
    xmpp_sub._handle_client_directory_discovered(dir_rooms)
    discovered = xmpp_sub.get_directory_rooms()
    assert len(discovered) == 2

    # Test hardened SSL/TLS context configuration & CodeQL compliance
    import ssl
    std_ctx = xmpp_sub.client._build_ssl_context(allow_self_signed=False)
    assert std_ctx.minimum_version == ssl.TLSVersion.TLSv1_2, "TLS minimum version must be TLSv1.2+"
    assert (std_ctx.options & ssl.OP_NO_TLSv1) != 0, "TLSv1.0 must be explicitly disabled"
    assert (std_ctx.options & ssl.OP_NO_TLSv1_1) != 0, "TLSv1.1 must be explicitly disabled"
    assert (std_ctx.options & ssl.OP_NO_SSLv3) != 0, "SSLv3 must be explicitly disabled"
    assert std_ctx.check_hostname is True
    assert std_ctx.verify_mode == ssl.CERT_REQUIRED

    self_signed_ctx = xmpp_sub.client._build_ssl_context(allow_self_signed=True)
    assert self_signed_ctx.minimum_version == ssl.TLSVersion.TLSv1_2
    assert self_signed_ctx.check_hostname is False
    assert self_signed_ctx.verify_mode == ssl.CERT_NONE

    assert xmpp_sub.stop() is True
    print(f" -> XMPPChatSubsystem passed! Broadcast ping target: {parsed_bcast.target_system}, FC: {parsed_bcast.fc_name}")

    # 8. VOIP (Mumble) Subsystem Test
    print("[TEST] VOIPMumbleSubsystem ephemeral config, state events & channel text check...")
    voip_sub = VOIPMumbleSubsystem()
    assert voip_sub.initialize() is True
    assert voip_sub.start() is True

    voip_cfg = VOIPAccountConfig(
        host="mumble.alliance.net",
        port=64738,
        username="recon_pilot",
        password="test_ephemeral_voip_password",
        channel_path="Fleet 1",
        allow_self_signed_tls=False,
    )
    assert voip_cfg.username == "recon_pilot"
    assert voip_cfg.port == 64738
    # OPSEC: ephemeral credentials are wiped, never persisted
    voip_cfg.wipe_credentials()
    assert voip_cfg.password == ""
    assert voip_cfg.tokens == []

    # Connection state transitions flow through the EventBus without a live socket
    voip_states = []
    eb.subscribe(VOIPConnectionStateChangedEvent, lambda evt: voip_states.append(evt))
    voip_sub.active_config = VOIPAccountConfig(host="mumble.alliance.net", username="recon_pilot")
    voip_sub.client.set_state(VOIPConnectionState.CONNECTED)
    assert len(voip_states) >= 1
    assert voip_states[-1].state == VOIPConnectionState.CONNECTED.value
    assert voip_states[-1].host == "mumble.alliance.net"

    # Simulated channel text buffering + EventBus dispatch
    voip_texts = []
    eb.subscribe(VOIPTextMessageEvent, lambda evt: voip_texts.append(evt))
    demo_msg = voip_sub.inject_simulated_message(sender="FleetCommander", body="Form up on the gate.")
    assert demo_msg.sender == "FleetCommander"
    assert demo_msg.body == "Form up on the gate."
    history = voip_sub.get_messages(limit=10)
    assert any(m.msg_id == demo_msg.msg_id for m in history)
    assert len(voip_texts) == 1
    assert voip_texts[0].body == "Form up on the gate."

    # Topology snapshot refresh (stubbed adapter snapshot, no live server required)
    def _stub_snapshot():
        return (
            [VOIPChannel(channel_id=0, name="Fleet 1", path="Fleet 1", parent_id=-1, user_count=2)],
            [
                VOIPUser(session_id=1, name="recon_pilot", channel_id=0, is_self=True),
                VOIPUser(session_id=2, name="WingCommander", channel_id=0),
            ],
            1,
        )
    voip_sub.client.snapshot_topology = _stub_snapshot
    topology_events = []
    eb.subscribe(VOIPChannelUpdatedEvent, lambda evt: topology_events.append(evt))
    voip_sub._handle_topology_changed()
    assert voip_sub.active_channel_id == 0
    assert len(voip_sub.get_channels()) == 1
    assert len(voip_sub.get_users()) == 2
    assert len(topology_events) == 1
    assert topology_events[0].channel_name == "Fleet 1"

    # Peer speaking telemetry
    speaking_events = []
    eb.subscribe(VOIPUserSpeakingEvent, lambda evt: speaking_events.append(evt))
    voip_sub._handle_speaking_changed(2, "WingCommander", 0, True)
    assert voip_sub.users[2].is_speaking is True
    assert len(speaking_events) == 1
    assert speaking_events[0].username == "WingCommander"

    # Offline guards: no live socket, so text send and PCM transmission fail closed
    assert voip_sub.send_channel_text(0, "should not transmit") is False
    assert voip_sub.client.push_outbound_pcm(b"\x00\x00" * 160) is False
    assert voip_sub.pop_inbound_pcm() == []

    status = voip_sub.get_status()
    assert status["connected"] is True
    assert status["channels_count"] == 1
    assert status["users_count"] == 2
    assert status["active_channel_id"] == 0

    assert voip_sub.stop() is True
    assert len(voip_sub.get_channels()) == 0
    print(" -> VOIPMumbleSubsystem passed! Channel text history & speaking telemetry verified.")

    print("\n[SUCCESS] ALL SUBSYSTEM TESTS PASSED CLEANLY!")
    return True


if __name__ == "__main__":
    if not test_subsystems():
        sys.exit(1)
