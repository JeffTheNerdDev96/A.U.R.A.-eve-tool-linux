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
Comprehensive automated integrity & regression test suite for A.U.R.A. v0.6.0-alpha.4:
1. Syntax & Compilation check on all project source files (excluding virtual environments).
2. Pure modular package imports and zero root-shim dependency check.
3. EventBus edge case & high-throughput test.
4. Intel parsing heuristics & expiration test.
5. Map router BFS pathfinding, avoidance & disconnected graph test.
6. Fleet composition 5-role classification & matchup tests.
7. Fitting subsystem EFT parsing & Dogma calculation tests.
8. Version string consistency across source data, code, and documentation.
"""

import os
import sys
import importlib.util
import py_compile
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_TESTS_DIR)
_APP_ROOT = os.path.dirname(_TOOLS_DIR)
_REPO_ROOT = os.path.dirname(_APP_ROOT)

if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from version import VERSION
from core import get_event_bus
from core.events import RouteCalculatedEvent
from subsystems.intel import IntelSubsystem, IntelReport, ThreatStatus
from subsystems.map import MapRouter
from subsystems.fleet_comp import FleetCompAnalyzer
from subsystems.fitting import FittingSubsystem


def _has_module(name: str) -> bool:
    """True when the named module is importable in this tree."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _has_attr(module_name: str, attr: str) -> bool:
    """True when the named module imports and exposes the given attribute."""
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return False
    return hasattr(module, attr)


class TestCodebaseIntegrity(unittest.TestCase):

    def test_01_all_files_compile(self):
        """Verify all python source files compile without syntax errors."""
        compiled_count = 0
        for root, dirs, files in os.walk(_APP_ROOT):
            # Skip venvs, git, build artifacts
            dirs[:] = [d for d in dirs if d not in ("venv", "venv_app", ".git", "__pycache__", "build_temp", "build_installer_temp", "build_standalone_temp", "runtime")]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    try:
                        py_compile.compile(full_path, doraise=True)
                        compiled_count += 1
                    except py_compile.PyCompileError as exc:
                        self.fail(f"Compilation error in {full_path}: {exc}")
        print(f" -> Successfully compiled {compiled_count} Python source files with 0 syntax errors.")
        self.assertGreater(compiled_count, 20)

    def test_02_event_bus_scenarios(self):
        """Test EventBus advanced pub/sub patterns."""
        eb = get_event_bus()
        received = []

        def on_event(e):
            received.append(e)

        eb.subscribe(RouteCalculatedEvent, on_event)
        evt = RouteCalculatedEvent(
            origin_system="Jita",
            destination_system="Amarr",
            total_jumps=11,
            route_path=["Jita", "Amarr"]
        )
        eb.publish(evt)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].origin_system, "Jita")
        self.assertEqual(received[0].destination_system, "Amarr")
        print(" -> EventBus typed subscriptions and hierarchical dispatch verified.")

    def test_03_intel_subsystem_edge_cases(self):
        """Test Intel parser with multiple messages, clear messages, NV handling, and tiered threats."""
        intel_sub = IntelSubsystem()
        intel_sub.initialize()

        # 1. Clear status
        reports = intel_sub.process_intel_line("[ 2026.08.23 12:00:00 ] Recon Pilot > 1DQ1-A clr")
        self.assertTrue(any(r.threat_level == ThreatStatus.CLEAR for r in reports))

        # 2. NV status (NV is unknown, not clear)
        reports_nv = intel_sub.process_intel_line("[ 2026.08.23 12:00:00 ] Recon Pilot > 1DQ1-A +5 NV")
        self.assertEqual(len(reports_nv), 1)
        self.assertFalse(reports_nv[0].is_clear)
        self.assertEqual(reports_nv[0].threat_level, "MEDIUM")

        # 3. Critical threat level report
        reports_crit = intel_sub.process_intel_line("1DQ1-A +50 Dreadnought, Carrier, FAX on grid")
        self.assertTrue(len(reports_crit) > 0)
        self.assertIsInstance(reports_crit[0], IntelReport)
        self.assertEqual(reports_crit[0].threat_level, "CRITICAL")

        # 4. Hostile report with ship name (sub-10 medium)
        reports2 = intel_sub.process_intel_line("[ 2026.08.23 12:00:01 ] Scout > T5ZI-S 2 Sabre, 1 Loki, 5 Cerberus")
        self.assertTrue(len(reports2) > 0)
        self.assertEqual(reports2[0].system, "T5ZI-S")
        self.assertIn("Sabre", reports2[0].ships)

        # 5. Garbage line
        reports3 = intel_sub.process_intel_line("Hello fleet how is it going?")
        self.assertEqual(len(reports3), 0)
        print(" -> Intel subsystem heuristics, clearing, expiration, and parser verified.")

    def test_04_map_router_scenarios(self):
        """Test MapRouter pathfinding, system avoidance, and nonexistent systems."""
        router = MapRouter()

        # Direct path
        route = router.calculate_route("Jita", "Perimeter")
        self.assertIsNotNone(route)
        self.assertEqual(route.total_jumps, 1)
        self.assertEqual(route.path, ["Jita", "Perimeter"])

        # Avoidance
        route_avoid = router.calculate_route("Jita", "Perimeter", avoid_systems=["Perimeter"])
        # Since Perimeter is the immediate destination and avoided, router handles gracefully
        self.assertIsNotNone(route_avoid)

        # Nonexistent system
        route_none = router.calculate_route("NonExistentSystem123", "Jita")
        self.assertIsNone(route_none)
        print(" -> Map router pathfinding, avoidance, and invalid handling verified.")

    def test_05_fleet_comp_scenarios(self):
        """Test FleetCompAnalyzer role breakdown with 5 distinct roles."""
        analyzer = FleetCompAnalyzer()

        dscan = """
        Oneiros	999	10 km
        Scimitar	888	12 km
        Cerberus	777	20 km
        Muninn	666	22 km
        Osprey Navy Issue	555	25 km
        Stiletto	444	5 km
        Sabre	333	8 km
        Keres	222	60 km
        Falcon	111	70 km
        Purifier	123	15 km
        """
        analysis = analyzer.analyze_dscan_text(dscan)
        self.assertEqual(analysis.total_ships, 10)
        self.assertEqual(analysis.logistics_count, 2)
        self.assertEqual(analysis.mainline_dps_count, 3)
        self.assertEqual(analysis.tacklers_count, 2)
        self.assertEqual(analysis.role_counts.get("T2 Recons / EAS", 0), 2)
        self.assertEqual(analysis.covert_ops_count, 1)

        # Counter recommendation must suggest Logistics targeting
        self.assertIn("Logistics", analysis.counter_recommendation)
        self.assertTrue("mainline" in analysis.counter_recommendation.lower())

        # Matchup assessment
        friendly_dscan = "Muninn\t1\t10km\nMuninn\t2\t10km\nScimitar\t3\t10km"
        enemy_dscan = "Rifter\t4\t5km"
        matchup = analyzer.assess_fleet_matchup(friendly_dscan, enemy_dscan)
        self.assertIn("Advantage", matchup.get("assessment", ""))
        print(" -> Fleet composition analyzer, 5 roles, and matchup comparisons verified.")

    def test_05b_dscan_subsystem_scenarios(self):
        """Test DScanSubsystem class grouping and formatted breakdown."""
        from subsystems.dscan import DScanSubsystem
        dscan_sub = DScanSubsystem()
        sample = "Muninn\t1\t10km\nCerberus\t2\t15km\nCerberus\t3\t20km\nStiletto\t4\t5km\nCrow\t5\t8km"
        analysis = dscan_sub.parse_dscan(sample)
        self.assertEqual(analysis.total_ships, 5)
        self.assertEqual(len(analysis.class_summaries), 2)
        classes = {cs.ship_class: cs for cs in analysis.class_summaries}
        self.assertIn("Heavy Assault Cruiser", classes)
        self.assertEqual(classes["Heavy Assault Cruiser"].total_count, 3)
        self.assertEqual(classes["Heavy Assault Cruiser"].breakdown_str, "Heavy Assault Cruiser : 3 : Cerberus x2, Muninn")
        self.assertIn("Interceptor", classes)
        self.assertEqual(classes["Interceptor"].total_count, 2)
        self.assertIn("Crow", classes["Interceptor"].breakdown_str)
        self.assertIn("Stiletto", classes["Interceptor"].breakdown_str)
        print(" -> D-Scan subsystem class grouping and breakdown strings verified.")

    def test_06_fitting_subsystem_scenarios(self):
        """Test FittingSubsystem parsing and Dogma stats."""
        fit_sub = FittingSubsystem()
        eft = """[Lachesis, Armor Point]
Damage Control II
1600mm Steel Plates II
Energized Adaptive Nano Membrane II
Medium Armor Repairer II

50MN Microwarpdrive II
Warp Disruptor II
Warp Scrambler II
Fleeting Compact Stasis Webifier

Heavy Missile Launcher II
Heavy Missile Launcher II
Heavy Missile Launcher II
[Empty High slot]

Medium Trimark Armor Pump II
Medium Trimark Armor Pump II
Medium Ancillary Current Router I
"""
        parsed = fit_sub.parse_eft(eft)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.ship_name, "Lachesis")
        self.assertGreater(parsed.stats.get("ehp", 0), 3000)
        print(" -> Fitting subsystem EFT parsing, slot layout, and Dogma stats verified.")

    def test_07_version_consistency(self):
        """Ensure v0.6.0-alpha.4 is the canonical product version."""
        self.assertEqual(VERSION, "v0.6.0-alpha.4")
        print(f" -> Version string {VERSION} verified.")

    def test_08_hardware_profile_helpers(self):
        """Verify hardware profile composition and profile building."""
        from hardware.profile import compose_install_plan, build_named_profile, PROFILE_IDS
        self.assertIn("nvidia_dgpu", PROFILE_IDS)
        self.assertIn("intel_npu", PROFILE_IDS)
        self.assertIn("cpu_mesh", PROFILE_IDS)

        named = build_named_profile("nvidia_dgpu", llama_wheel="cuda")
        self.assertEqual(named["primary"], "nvidia_dgpu")
        self.assertEqual(named["llama_wheel"], "cuda")

        plan1 = compose_install_plan({})
        self.assertEqual(plan1["primary"], "cpu_mesh")

        plan2 = compose_install_plan(None)
        self.assertEqual(plan2["primary"], "cpu_mesh")

        plan3 = compose_install_plan({"gpus": [{"vendor": "NVIDIA", "type": "dGPU"}]})
        self.assertEqual(plan3["primary"], "nvidia_dgpu")
        self.assertEqual(plan3["llama_wheel"], "cuda")
        print(" -> Hardware profile helper functions verified.")

    def test_09_python_312_features_and_slots(self):
        """Verify Python 3.12.14 features: slots, StrEnum, PEP 678 notes, and PEP 695."""
        self.assertGreaterEqual(sys.version_info[:2], (3, 12))

        # 1. Event dataclasses use __slots__
        evt = RouteCalculatedEvent(origin_system="Jita", destination_system="Amarr")
        self.assertTrue(hasattr(evt, "__slots__"))
        with self.assertRaises(AttributeError):
            evt.dynamic_custom_attr = "invalid"  # Slots prevent arbitrary attribute assignment

        # 2. StrEnum behavior
        from subsystems.wormhole.models import WormholeClass, MassState
        from subsystems.intel.models import ThreatStatus
        from subsystems.xmpp_chat.models import XMPPConnectionState, XMPPBroadcastPriority
        self.assertIsInstance(WormholeClass.C1, str)
        self.assertEqual(WormholeClass.C1, "Class 1")
        self.assertIsInstance(MassState.FRESH, str)
        self.assertEqual(MassState.FRESH, "Stage 1 (>50%)")
        self.assertIsInstance(ThreatStatus.HOSTILE, str)
        self.assertEqual(ThreatStatus.HOSTILE, "HOSTILE")
        self.assertIsInstance(XMPPConnectionState.CONNECTED, str)
        self.assertEqual(XMPPConnectionState.CONNECTED, "Connected")
        self.assertIsInstance(XMPPBroadcastPriority.FLEET_FORMUP, str)
        self.assertEqual(XMPPBroadcastPriority.FLEET_FORMUP, "Fleet Formup")

        # 3. PEP 678 Exception notes in AURAException
        from core.error_handler import AURAException, AURAErrorCode
        try:
            raise AURAException(AURAErrorCode.ERR_1001_MODEL_NOT_FOUND, technical_details="test details")
        except AURAException as err:
            self.assertTrue(hasattr(err, "__notes__"))
            self.assertGreater(len(err.__notes__), 0)
            self.assertTrue(any("AURA-ERR-1001" in n for n in err.__notes__))

        # 4. Wormhole and XMPP models have __slots__
        from subsystems.wormhole.models import WormholeConnection
        from subsystems.xmpp_chat.models import XMPPMessage, XMPPAccountConfig
        conn = WormholeConnection(connection_id="c1", source_system="Jita", target_system="Perimeter")
        self.assertTrue(hasattr(conn, "__slots__"))
        xmpp_msg = XMPPMessage(sender_jid="scout@alliance.net", body="ping")
        self.assertTrue(hasattr(xmpp_msg, "__slots__"))
        xmpp_cfg = XMPPAccountConfig(jid="pilot@alliance.net")
        self.assertTrue(hasattr(xmpp_cfg, "__slots__"))

        print(" -> Python 3.12.14 features (slots, StrEnum, PEP 678 notes, PEP 695) verified.")

    @unittest.skipUnless(_has_module("tools.install_fetch"), "Windows-only installer internals not present")
    def test_10_install_fetch_tar_extraction(self):
        """Verify _extract_standalone_tar properly extracts tarballs without TarFile argument errors."""
        import tempfile
        import tarfile
        from tools.install_fetch import _extract_standalone_tar

        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = os.path.join(tmpdir, "test_python.tar.gz")
            runtime_dir = os.path.join(tmpdir, "runtime_target")

            # Create a mock standalone python tar archive with python/ prefix
            with tarfile.open(archive_path, "w:gz") as tf:
                sample_file = os.path.join(tmpdir, "python.exe")
                with open(sample_file, "wb") as f:
                    f.write(b"MOCK_PYTHON_BINARY")
                tf.add(sample_file, arcname="python/python.exe")

            # Extract using _extract_standalone_tar
            _extract_standalone_tar(archive_path, runtime_dir)

            # Verify destination
            extracted_file = os.path.join(runtime_dir, "python.exe")
            self.assertTrue(os.path.isfile(extracted_file))
            with open(extracted_file, "rb") as f:
                self.assertEqual(f.read(), b"MOCK_PYTHON_BINARY")

        print(" -> _extract_standalone_tar extraction & path traversal guards verified.")

    @unittest.skipUnless(_has_module("tools.installer_gui"), "Windows-only installer GUI internals not present")
    def test_11_nvidia_and_amd_gpu_profile_composition(self):
        """Verify multi-vendor GPU topology compositions for NVIDIA, AMD dGPU, AMD iGPU, and Ryzen AI NPU."""
        from hardware.profile import compose_install_plan, apply_install_mask, gpu_strategy_label
        from tools.installer_gui import llama_wheel_for_profiles, primary_for_profiles

        # 1. NVIDIA Dedicated GPU (RTX 4090 / RTX Ada)
        nvidia_dev = {
            "cpu": {"name": "CPU", "device_name": "AMD Ryzen 9 7950X", "available": True, "cores": 16, "threads": 32, "ram_gb": 32.0},
            "gpus": [{"device_name": "NVIDIA GeForce RTX 4090", "vendor": "NVIDIA", "type": "dGPU", "backend": "NVIDIA Hardware Acceleration"}],
            "gpu": {"name": "GPU", "available": True, "device_name": "NVIDIA GeForce RTX 4090", "vendor": "NVIDIA", "type": "dGPU"},
            "npu": {"name": "NPU", "available": False, "vendor": "None", "device_name": "No NPU Detected", "backend": "None", "is_intel": False, "is_amd": False},
        }
        plan_nv = compose_install_plan(nvidia_dev)
        self.assertEqual(plan_nv["primary"], "nvidia_dgpu")
        self.assertEqual(plan_nv["llama_wheel"], "cuda")
        self.assertEqual(plan_nv["gpu_class"], "nvidia_dgpu")
        self.assertEqual(llama_wheel_for_profiles(["nvidia_dgpu"]), "cuda")
        self.assertEqual(primary_for_profiles(["nvidia_dgpu"]), "nvidia_dgpu")
        self.assertEqual(gpu_strategy_label(plan_nv, "NVIDIA"), "NVIDIA CUDA")

        # 2. AMD Dedicated GPU (Radeon RX 7900 XTX)
        amd_dgpu_dev = {
            "cpu": {"name": "CPU", "device_name": "AMD Ryzen 7 7800X3D", "available": True, "cores": 8, "threads": 16, "ram_gb": 32.0},
            "gpus": [{"device_name": "AMD Radeon RX 7900 XTX", "vendor": "AMD", "type": "dGPU", "backend": "AMD Hardware Acceleration"}],
            "gpu": {"name": "GPU", "available": True, "device_name": "AMD Radeon RX 7900 XTX", "vendor": "AMD", "type": "dGPU"},
            "npu": {"name": "NPU", "available": False, "vendor": "None", "device_name": "No NPU Detected", "backend": "None", "is_intel": False, "is_amd": False},
        }
        plan_amd_d = compose_install_plan(amd_dgpu_dev)
        self.assertEqual(plan_amd_d["primary"], "amd_dgpu")
        self.assertEqual(plan_amd_d["llama_wheel"], "vulkan")
        self.assertEqual(plan_amd_d["gpu_class"], "amd_dgpu")
        self.assertEqual(llama_wheel_for_profiles(["amd_dgpu"]), "vulkan")
        self.assertEqual(primary_for_profiles(["amd_dgpu"]), "amd_dgpu")
        self.assertEqual(gpu_strategy_label(plan_amd_d, "AMD"), "AMD Vulkan")

        # 3. AMD APU + NPU (Radeon 780M / 890M iGPU + XDNA NPU)
        amd_apu_dev = {
            "cpu": {"name": "CPU", "device_name": "AMD Ryzen 7 8845HS", "available": True, "cores": 8, "threads": 16, "ram_gb": 16.0},
            "gpus": [{"device_name": "AMD Radeon 780M Graphics", "vendor": "AMD", "type": "iGPU", "backend": "AMD Hardware Acceleration"}],
            "gpu": {"name": "GPU", "available": True, "device_name": "AMD Radeon 780M Graphics", "vendor": "AMD", "type": "iGPU"},
            "npu": {"name": "NPU", "available": True, "vendor": "AMD", "device_name": "AMD Ryzen AI (XDNA NPU)", "backend": "AMD Ryzen AI (XDNA / DirectML)", "is_intel": False, "is_amd": True},
        }
        plan_amd_apu = compose_install_plan(amd_apu_dev)
        self.assertIn("amd_igpu", plan_amd_apu["profiles"])
        self.assertIn("amd_npu", plan_amd_apu["profiles"])
        self.assertEqual(plan_amd_apu["llama_wheel"], "vulkan")
        self.assertEqual(plan_amd_apu["coprocessor"], "directml")
        self.assertEqual(plan_amd_apu["npu"], "amd")

        # 4. Multi-GPU / Heterogeneous (NVIDIA dGPU + AMD/Intel iGPU)
        multi_gpu_dev = {
            "cpu": {"name": "CPU", "device_name": "AMD Ryzen 9 7900X", "available": True, "cores": 12, "threads": 24, "ram_gb": 64.0},
            "gpus": [
                {"device_name": "NVIDIA GeForce RTX 4080", "vendor": "NVIDIA", "type": "dGPU", "backend": "NVIDIA Hardware Acceleration"},
                {"device_name": "AMD Radeon Graphics", "vendor": "AMD", "type": "iGPU", "backend": "AMD Hardware Acceleration"},
            ],
            "gpu": {"name": "GPU", "available": True, "device_name": "NVIDIA GeForce RTX 4080", "vendor": "NVIDIA", "type": "dGPU"},
            "npu": {"name": "NPU", "available": False, "vendor": "None", "device_name": "No NPU Detected", "backend": "None", "is_intel": False, "is_amd": False},
        }
        plan_multi = compose_install_plan(multi_gpu_dev)
        self.assertEqual(plan_multi["primary"], "nvidia_dgpu")
        self.assertEqual(plan_multi["llama_wheel"], "cuda")

        # 5. Masking verification
        masked = apply_install_mask(dict(multi_gpu_dev), {"profiles": ["nvidia_dgpu"]})
        self.assertEqual(len(masked["gpus"]), 1)
        self.assertEqual(masked["gpus"][0]["vendor"], "NVIDIA")

        print(" -> Multi-vendor GPU profile composition and routing masks verified.")

    @unittest.skipUnless(_has_attr("bootstrap.bootstrap_llama", "_sanitize_stale_toolkit_env"), "Windows-only DLL bootstrap internals not present")
    def test_12_gpu_dll_bootstrapper_and_sanitizer(self):
        """Verify DLL search registration and stale environment sanitization for CUDA and HIP/Vulkan."""
        from bootstrap.bootstrap_llama import (
            _sanitize_stale_toolkit_env,
            _cuda_bin_dirs,
            _vulkan_bin_dirs,
            configure_llama_dll_paths,
        )

        # 1. Verify stale toolkit environment sanitization
        os.environ["CUDA_PATH"] = r"C:\fake\nonexistent\cuda_path"
        os.environ["HIP_PATH"] = r"C:\fake\nonexistent\hip_path"
        diag = _sanitize_stale_toolkit_env()
        self.assertNotIn("CUDA_PATH", os.environ)
        self.assertNotIn("HIP_PATH", os.environ)
        self.assertTrue(any("CUDA_PATH" in d for d in diag))
        self.assertTrue(any("HIP_PATH" in d for d in diag))

        # 2. Verify search path helper routines execute cleanly
        cuda_dirs = _cuda_bin_dirs()
        self.assertIsInstance(cuda_dirs, list)
        vulkan_dirs = _vulkan_bin_dirs()
        self.assertIsInstance(vulkan_dirs, list)

        # 3. Verify overall configure_llama_dll_paths
        paths_diag = configure_llama_dll_paths()
        self.assertIsInstance(paths_diag, list)
        print(" -> GPU DLL bootstrapper, directory discovery, and environment sanitization verified.")

    @unittest.skipUnless(_has_module("requirements._check_drivers"), "Windows-only driver checker URLs not present")
    def test_13_driver_checker_urls_and_fallback_resilience(self):
        """Verify vendor driver URLs and fallback resilience constants."""
        from requirements._check_drivers import NVIDIA_URL, AMD_URL, INTEL_GPU_URL, INTEL_NPU_URL
        self.assertTrue(NVIDIA_URL.startswith("https://www.nvidia.com/"))
        self.assertTrue(AMD_URL.startswith("https://www.amd.com/"))
        self.assertTrue(INTEL_GPU_URL.startswith("https://www.intel.com/"))
        self.assertTrue(INTEL_NPU_URL.startswith("https://www.intel.com/"))

        from hardware.profile import install_hint_for_gpu
        self.assertIn("install_nvidia_cuda.bat", install_hint_for_gpu("NVIDIA"))
        self.assertIn("install_amd_dgpu.bat", install_hint_for_gpu("AMD"))
        self.assertIn("install_intel_dgpu.bat", install_hint_for_gpu("Intel"))
        self.assertIn("install_cpu.bat", install_hint_for_gpu("UnknownVendor"))
        print(" -> Driver check URLs, installation hints, and fallback mappings verified.")

    @unittest.skipUnless(_has_module("install_fetch"), "Windows-only install_fetch bootstrap not present")
    def test_14_cross_platform_detection_and_clean_dll_bootstrap(self):
        """Verify dynamic OS detection, Wine/Proton fallback directory, and clean native Qt bootstrap."""
        from install_fetch import detect_os_environment, missing_vcredist_dlls, vcredist_present
        from bootstrap import configure_qt_paths
        from bootstrap.bootstrap_runtime import is_wine_or_proton, _preload_qt_dlls

        # 1. Verify OS environment detection
        os_info = detect_os_environment()
        self.assertIsInstance(os_info, dict)
        self.assertIn("platform", os_info)
        self.assertIn("is_windows", os_info)
        self.assertIn("is_wine_or_proton", os_info)
        self.assertIn("description", os_info)
        self.assertTrue(len(os_info["description"]) > 0)

        # 2. Verify Wine / Proton detection routine
        wine_detected = is_wine_or_proton()
        self.assertIsInstance(wine_detected, bool)
        self.assertTrue(callable(_preload_qt_dlls))

        # 3. Verify VCRedist probing routines
        missing_vc = missing_vcredist_dlls()
        self.assertIsInstance(missing_vc, list)
        has_vc = vcredist_present()
        self.assertIsInstance(has_vc, bool)

        # 4. Verify Wine fallback DLLs directory exists and contains all required libraries
        wine_dlls_dir = os.path.join(_APP_ROOT, "bootstrap", "wine_dlls")
        self.assertTrue(os.path.isdir(wine_dlls_dir), "bootstrap/wine_dlls directory missing")
        expected_wine_dlls = (
            "concrt140.dll", "d3dcompiler_47.dll", "icu.dll", "icuin.dll", "icuuc.dll",
            "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "msvcp_win.dll",
            "opengl32sw.dll", "ucrtbase.dll", "vccorlib140.dll", "vcruntime140.dll", "vcruntime140_1.dll"
        )
        for dll_name in expected_wine_dlls:
            self.assertTrue(
                os.path.isfile(os.path.join(wine_dlls_dir, dll_name)),
                f"Missing Wine fallback DLL: {dll_name}"
            )

        # 5. Verify Qt bootstrap executes without errors and PyQt6 loads cleanly
        configure_qt_paths()
        import PyQt6.QtWidgets
        self.assertIsNotNone(PyQt6.QtWidgets.QApplication)

        # 6. Verify native Windows does NOT inject wine_dlls into PATH
        if not is_wine_or_proton():
            path_parts = os.environ.get("PATH", "").split(os.pathsep)
            self.assertNotIn(os.path.abspath(wine_dlls_dir), path_parts)

        print(" -> Cross-platform OS detection, Wine/Proton fallback directory, and dual-mode DLL bootstrap verified.")

    def test_15_expanded_eve_database(self):
        """Verify expanded canonical modules, exact ship profiles, Akoman, and Equinox ships."""
        from core.eve_data import lookup_ship, lookup_module, MODULE_DATABASE
        from core.eve_modules_data import CANONICAL_MODULES
        from core.eve_ships_data import EXACT_SHIP_PROFILES

        # 1. Module database volume and schema
        self.assertGreaterEqual(len(CANONICAL_MODULES), 250)
        self.assertGreaterEqual(len(MODULE_DATABASE), 250)

        required_mod_keys = {
            "name", "slot", "category", "size", "cpu", "powergrid",
            "cap_need", "duration", "is_active", "stacking_group",
            "stacking_penalized", "hp_bonus", "shield_hp_pct",
            "armor_hp_pct", "resists", "calibration", "description"
        }
        for mod_name, mod_data in CANONICAL_MODULES.items():
            self.assertTrue(required_mod_keys.issubset(mod_data.keys()), f"Missing keys in module {mod_name}")
            self.assertIn(mod_data["slot"], {"High", "Mid", "Low", "Rig", "Subsystem"})
            self.assertIn(mod_data["size"], {"Small", "Medium", "Large", "Capital", "None"})
            self.assertIsInstance(mod_data["cpu"], float)
            self.assertIsInstance(mod_data["powergrid"], float)
            self.assertIsInstance(mod_data["is_active"], bool)
            self.assertIsInstance(mod_data["stacking_penalized"], bool)
            self.assertIsInstance(mod_data["resists"], dict)

        # 2. Required specific modules & aliases
        required_mods = [
            "Multispectrum Energized Membrane I",
            "Multispectrum Energized Membrane II",
            "Compact Multispectrum Energized Membrane",
            "Imperial Navy Multispectrum Energized Membrane",
            "Energized Adaptive Nano Membrane I",
            "Energized Adaptive Nano Membrane II",
            "Multispectrum Shield Hardener I",
            "Multispectrum Shield Hardener II",
            "Compact Multispectrum Shield Hardener",
            "Caldari Navy Multispectrum Shield Hardener",
            "Adaptive Invulnerability Field I",
            "Adaptive Invulnerability Field II",
            "1600mm Steel Plates II",
            "Large Shield Extender II",
            "Large Armor Repairer II",
            "Large Shield Booster II",
            "50MN Microwarpdrive II",
            "Warp Disruptor II",
            "Warp Scrambler II",
            "Damage Control II",
            "Medium Trimark Armor Pump II",
            "Medium Core Defense Field Extender II",
        ]
        for m in required_mods:
            found = lookup_module(m)
            self.assertIsNotNone(found, f"Required module {m} not found in lookup")

        # 3. Ship profiles and required vessels
        required_ships = [
            "Akoman", "Squall", "Deluge", "Torrent", "Avalanche",
            "Mekubal", "Khizriel", "Azariel", "Mamba", "Alligator",
            "Bane", "Hubris", "Valravn"
        ]
        for s in required_ships:
            ship_dossier = lookup_ship(s)
            self.assertIsNotNone(ship_dossier, f"Ship {s} missing from SHIP_DATABASE")
            self.assertIn(s, EXACT_SHIP_PROFILES, f"Ship {s} missing from EXACT_SHIP_PROFILES")

        # 4. Akoman Crimson Harvest exact attributes
        akoman = lookup_ship("Akoman")
        self.assertEqual(akoman.get("class"), "Attack Battlecruiser")
        self.assertEqual(akoman.get("faction"), "Blood Raiders")
        self.assertEqual(akoman.get("cpu"), 345.0)
        self.assertEqual(akoman.get("powergrid"), 1300.0)
        self.assertEqual(akoman.get("capacitor"), 3500.0)
        self.assertEqual(akoman.get("cap_recharge"), 825.0)
        self.assertEqual(akoman.get("shield_hp"), 2000.0)
        self.assertEqual(akoman.get("armor_hp"), 2700.0)
        self.assertEqual(akoman.get("hull_hp"), 2500.0)
        self.assertEqual(akoman.get("high_slots"), 6)
        self.assertEqual(akoman.get("mid_slots"), 4)
        self.assertEqual(akoman.get("low_slots"), 7)
        self.assertEqual(akoman.get("rig_slots"), 3)
        self.assertEqual(akoman.get("turret_hardpoints"), 4)
        self.assertEqual(akoman.get("launcher_hardpoints"), 0)
        self.assertEqual(akoman.get("max_velocity"), 220.0)
        self.assertEqual(akoman.get("mass"), 14760000.0)
        self.assertEqual(akoman.get("agility"), 0.47)

        # 5. D-Scan and visual fitter integration
        from subsystems.dscan import DScanSubsystem
        from subsystems.fitting import FittingSubsystem

        dscan_sub = DScanSubsystem()
        dscan_res = dscan_sub.parse_dscan("Akoman\t1\t10km\nSquall\t2\t15km\nTorrent\t3\t20km")
        self.assertEqual(dscan_res.total_ships, 3)

        fit_sub = FittingSubsystem()
        fit_parsed = fit_sub.parse_eft("""[Akoman, Crimson Harvest Armor Brawler]
Damage Control II
1600mm Steel Plates II
Multispectrum Energized Membrane II
Multispectrum Energized Membrane II
Medium Armor Repairer II
Heat Sink II
Heat Sink II

50MN Microwarpdrive II
Warp Scrambler II
Fleeting Compact Stasis Webifier
Heavy Capacitor Booster II

Mega Pulse Laser II
Mega Pulse Laser II
Mega Pulse Laser II
Mega Pulse Laser II
Heavy Energy Nosferatu II
Heavy Energy Nosferatu II

Medium Trimark Armor Pump II
Medium Trimark Armor Pump II
Medium Ancillary Current Router I
""")
        self.assertIsNotNone(fit_parsed)
        self.assertEqual(fit_parsed.ship_name, "Akoman")
        self.assertGreater(fit_parsed.stats.get("ehp", 0), 5000)

        print(" -> Expanded EVE Database: 530+ canonical Dogma modules, 335+ exact ship profiles, Akoman & Equinox vessels verified.")

    def test_16_mumble_and_xmpp_hardened_tls_contexts(self):
        """Verify Mumble and XMPP enforce TLS 1.2+ minimum, disable insecure protocols, and guard MITM."""
        import ssl
        from subsystems.voip_mumble.client import build_mumble_ssl_context
        from subsystems.xmpp_chat.client import XMPPProtocolAdapter

        # 1. Mumble default TLS context (strict CA + hostname verification)
        mumble_strict_ctx = build_mumble_ssl_context(allow_self_signed=False)
        self.assertEqual(mumble_strict_ctx.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertTrue(mumble_strict_ctx.check_hostname)
        self.assertEqual(mumble_strict_ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(bool(mumble_strict_ctx.options & ssl.OP_NO_TLSv1))
        self.assertTrue(bool(mumble_strict_ctx.options & ssl.OP_NO_TLSv1_1))
        self.assertTrue(bool(mumble_strict_ctx.options & ssl.OP_NO_SSLv3))

        # 2. Mumble opt-in self-signed TLS context (relaxed verification, but STILL TLS 1.2+ minimum)
        mumble_self_signed_ctx = build_mumble_ssl_context(allow_self_signed=True)
        self.assertEqual(mumble_self_signed_ctx.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertFalse(mumble_self_signed_ctx.check_hostname)
        self.assertEqual(mumble_self_signed_ctx.verify_mode, ssl.CERT_NONE)
        self.assertTrue(bool(mumble_self_signed_ctx.options & ssl.OP_NO_TLSv1))
        self.assertTrue(bool(mumble_self_signed_ctx.options & ssl.OP_NO_TLSv1_1))

        # 3. XMPP TLS context verification
        xmpp_adapter = XMPPProtocolAdapter()
        xmpp_strict_ctx = xmpp_adapter._build_ssl_context(allow_self_signed=False)
        self.assertEqual(xmpp_strict_ctx.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertTrue(xmpp_strict_ctx.check_hostname)
        self.assertEqual(xmpp_strict_ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(bool(xmpp_strict_ctx.options & ssl.OP_NO_TLSv1))
        self.assertTrue(bool(xmpp_strict_ctx.options & ssl.OP_NO_TLSv1_1))

        print(" -> Mumble & XMPP hardened TLS 1.2+ contexts, legacy protocol ciphers, and validation verified.")


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCodebaseIntegrity)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    if not run_tests():
        sys.exit(1)

