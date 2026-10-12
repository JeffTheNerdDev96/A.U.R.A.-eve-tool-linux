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
Hardware Topology Detection & Dynamic Multi-Vendor Hardware Acceleration Router - Linux Native.
Customized for Adaptive Underworld Recon Array (A.U.R.A.) on Ubuntu / Debian / Fedora / Arch Linux.
Supports:
  - Linux Vulkan Acceleration (Mesa RADV AMD, Intel ANV, NVIDIA proprietary)
  - NVIDIA CUDA 12.x on Linux
  - Intel NPU / AMD Ryzen AI NPU via Linux Level Zero & sysfs/accel
  - Multi-threaded CPU Vector Mesh (AVX2 / AVX-512 SIMD)
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import platform
import psutil
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from core.config import config
from core.error_handler import AURAErrorCode, log_diagnostic_error
from core.paths import get_app_root
from .profile import (
    apply_install_mask,
    gpu_strategy_label,
    load_install_profile,
    standby_label,
    summarize_devices,
    DeviceMap,
    HardwareProfile,
)

_CACHED_HARDWARE_DEVICES: DeviceMap | None = None
_PHYS_CORES: int = psutil.cpu_count(logical=False) or 4
_LOGICAL_CORES: int = psutil.cpu_count(logical=True) or 8

_OPENVINO_PROBE_SCRIPT = (
    "import json\n"
    "try:\n"
    "    import openvino as ov\n"
    "    core = ov.Core()\n"
    "    print(json.dumps({'devices': list(core.available_devices)}))\n"
    "except Exception as exc:\n"
    "    print(json.dumps({'error': str(exc)}))\n"
)

_OPENVINO_PROFILE_KEYS = frozenset({"intel_npu", "intel_igpu", "intel_dgpu"})


def _is_missing_openvino_error(err: str) -> bool:
    low = (err or "").lower()
    return "no module named 'openvino'" in low or "no module named openvino" in low


def _openvino_importable() -> bool:
    return importlib.util.find_spec("openvino") is not None


def _get_linux_cpu_model() -> str:
    """Reads processor model name from /proc/cpuinfo or platform info."""
    try:
        if os.path.isfile("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "model name" in line:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip()
    except Exception:
        pass
    proc = platform.processor()
    if proc:
        return proc
    return "Generic Linux x86_64 CPU"


def _probe_nvidia_gpus() -> List[Dict[str, Any]]:
    """Probes NVIDIA GPUs via nvidia-smi on Linux."""
    gpus = []
    if not shutil.which("nvidia-smi"):
        return gpus
    try:
        cmd = ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
        if res.returncode == 0 and res.stdout:
            for line in res.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    name = parts[0]
                    vram_mb = int(parts[1]) if parts[1].isdigit() else 8192
                    gpus.append({
                        "name": name,
                        "vendor": "NVIDIA",
                        "type": "Dedicated GPU",
                        "vram_gb": round(vram_mb / 1024, 1),
                        "driver": parts[2] if len(parts) > 2 else "NVIDIA Linux Driver",
                        "is_integrated": False,
                    })
    except Exception:
        pass
    return gpus


def _probe_sysfs_gpus() -> List[Dict[str, Any]]:
    """Probes GPUs via Linux sysfs /sys/class/drm."""
    gpus = []
    card_dirs = glob.glob("/sys/class/drm/card[0-9]")
    for cdir in sorted(card_dirs):
        try:
            device_dir = os.path.join(cdir, "device")
            if not os.path.isdir(device_dir):
                continue
            vendor_file = os.path.join(device_dir, "vendor")
            device_file = os.path.join(device_dir, "device")
            if not (os.path.isfile(vendor_file) and os.path.isfile(device_file)):
                continue

            with open(vendor_file, "r") as vf:
                vendor_hex = vf.read().strip().lower()

            vendor_name = "Generic GPU"
            is_intel = "0x8086" in vendor_hex
            is_amd = "0x1002" in vendor_hex
            is_nvidia = "0x10de" in vendor_hex

            if is_nvidia:
                vendor_name = "NVIDIA"
            elif is_amd:
                vendor_name = "AMD"
            elif is_intel:
                vendor_name = "Intel"

            # Check VRAM if available
            vram_gb = 4.0
            vram_file = os.path.join(device_dir, "mem_info_vram_total")
            if os.path.isfile(vram_file):
                try:
                    with open(vram_file, "r") as mf:
                        bytes_total = int(mf.read().strip())
                        vram_gb = round(bytes_total / (1024 ** 3), 1)
                except Exception:
                    pass

            gpu_type = "Dedicated GPU" if vram_gb >= 3.0 else "Integrated GPU"
            gpus.append({
                "name": f"{vendor_name} Graphics Controller",
                "vendor": vendor_name,
                "type": gpu_type,
                "vram_gb": vram_gb,
                "driver": "Mesa / Linux DRM",
                "is_integrated": gpu_type == "Integrated GPU",
            })
        except Exception:
            continue
    return gpus


def _probe_lspci_hardware() -> Tuple[List[Dict[str, Any]], bool, bool]:
    """Probes PCI devices via lspci on Linux for GPUs and NPUs."""
    gpus: List[Dict[str, Any]] = []
    has_intel_npu = False
    has_amd_npu = False

    if not shutil.which("lspci"):
        return gpus, has_intel_npu, has_amd_npu

    try:
        res = subprocess.run(["lspci", "-nn"], capture_output=True, text=True, timeout=3.0)
        if res.returncode == 0 and res.stdout:
            for line in res.stdout.strip().splitlines():
                low = line.lower()
                # Check for Intel NPU (VPU / AI Boost)
                if ("8086:7d1d" in low or "8086:ad1d" in low or "intel" in low and ("vpu" in low or "npu" in low or "ai boost" in low)):
                    has_intel_npu = True
                # Check for AMD Ryzen AI NPU (XDNA)
                if ("amd" in low or "advanced micro devices" in low) and ("ipux" in low or "xdna" in low or "npu" in low):
                    has_amd_npu = True
                # Check for VGA / 3D / Display controller
                if "vga compatible controller" in low or "3d controller" in low or "display controller" in low:
                    if "nvidia" in low:
                        gpus.append({
                            "name": line.split(":", 2)[-1].strip(),
                            "vendor": "NVIDIA",
                            "type": "Dedicated GPU",
                            "vram_gb": 8.0,
                            "driver": "NVIDIA Linux Driver",
                            "is_integrated": False,
                        })
                    elif "amd" in low or "advanced micro devices" in low or "radeon" in low:
                        is_igpu = "integrated" in low or "apu" in low or "vega" in low or "680m" in low or "780m" in low or "890m" in low
                        gpus.append({
                            "name": line.split(":", 2)[-1].strip(),
                            "vendor": "AMD",
                            "type": "Integrated GPU" if is_igpu else "Dedicated GPU",
                            "vram_gb": 2.0 if is_igpu else 8.0,
                            "driver": "Mesa RADV / AMDGPU",
                            "is_integrated": is_igpu,
                        })
                    elif "intel" in low:
                        is_dgpu = "arc" in low or "battlemage" in low
                        gpus.append({
                            "name": line.split(":", 2)[-1].strip(),
                            "vendor": "Intel",
                            "type": "Dedicated GPU" if is_dgpu else "Integrated GPU",
                            "vram_gb": 8.0 if is_dgpu else 2.0,
                            "driver": "Mesa ANV / Intel OpenVINO",
                            "is_integrated": not is_dgpu,
                        })
    except Exception:
        pass
    return gpus, has_intel_npu, has_amd_npu


class HardwareDetector:
    """
    Discovers and classifies available compute hardware on Linux hosts.
    Scans for NVIDIA, AMD, and Intel GPUs, Intel/AMD NPUs, and multi-core CPU topologies.
    """
    def __init__(
        self,
        force_rescan: bool = False,
        apply_profile: bool = True,
        skip_openvino_probe: bool = False,
    ):
        global _CACHED_HARDWARE_DEVICES
        self._skip_openvino_probe = skip_openvino_probe
        if _CACHED_HARDWARE_DEVICES is not None and not force_rescan and apply_profile:
            self.devices = _CACHED_HARDWARE_DEVICES
        else:
            self.devices = self.scan_devices(
                apply_profile=apply_profile,
                skip_openvino_probe=skip_openvino_probe,
            )
            if apply_profile:
                _CACHED_HARDWARE_DEVICES = self.devices

    def scan_devices(
        self,
        apply_profile: bool = True,
        skip_openvino_probe: bool = False,
    ) -> DeviceMap:
        # 1. CPU Detection
        cpu_name = _get_linux_cpu_model()
        phys_cores = _PHYS_CORES
        logical_threads = _LOGICAL_CORES

        devices = {
            "cpu": {
                "name": "CPU",
                "device_name": cpu_name,
                "available": True,
                "cores": phys_cores,
                "threads": logical_threads,
                "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
            },
            "gpus": [],
            "gpu": {
                "name": "GPU",
                "available": False,
                "device_name": "No GPU Detected",
                "vendor": "Generic",
                "type": "None",
                "vram_gb": 0.0,
                "driver": "None",
                "is_integrated": False,
            },
            "intel_npu": {
                "name": "Intel NPU",
                "available": False,
                "device_name": "Intel NPU",
                "vendor": "Intel",
                "backend": "None",
                "generation": "None",
                "pnp_hardware_id": None,
                "pnp_device_desc": None,
                "pnp_matched": False,
                "driver_level_zero": False,
                "status": "Inactive",
                "notes": "",
            },
            "amd_npu": {
                "name": "AMD Ryzen AI NPU",
                "available": False,
                "device_name": "AMD Ryzen AI NPU",
                "vendor": "AMD",
                "generation": "None",
                "architecture": "None",
                "pnp_hardware_id": None,
                "pnp_device_desc": None,
                "pnp_matched": False,
                "driver_installed": False,
                "status": "Inactive",
                "notes": "",
            },
            "openvino_devices": [],
            "openvino_available": False,
            "openvino_probe_error": None,
        }

        # 2. GPU Detection (NVIDIA SMI -> lspci -> sysfs)
        detected_gpus = _probe_nvidia_gpus()
        if not detected_gpus:
            lspci_gpus, l_intel_npu, l_amd_npu = _probe_lspci_hardware()
            detected_gpus = lspci_gpus
            if l_intel_npu:
                devices["intel_npu"]["available"] = True
                devices["intel_npu"]["status"] = "Active"
                devices["intel_npu"]["notes"] = "Intel AI Boost VPU/NPU detected via PCI"
            if l_amd_npu:
                devices["amd_npu"]["available"] = True
                devices["amd_npu"]["status"] = "Active"
                devices["amd_npu"]["notes"] = "AMD Ryzen AI XDNA NPU detected via PCI"

        if not detected_gpus:
            detected_gpus = _probe_sysfs_gpus()

        if detected_gpus:
            devices["gpus"] = detected_gpus
            # Pick primary GPU: prioritize Dedicated over Integrated
            primary = next((g for g in detected_gpus if not g.get("is_integrated", False)), detected_gpus[0])
            devices["gpu"] = {
                "name": primary.get("name", "GPU"),
                "available": True,
                "device_name": primary.get("name", "GPU"),
                "vendor": primary.get("vendor", "Generic"),
                "type": primary.get("type", "Dedicated GPU"),
                "vram_gb": primary.get("vram_gb", 4.0),
                "driver": primary.get("driver", "Linux DRM"),
                "is_integrated": primary.get("is_integrated", False),
            }

        # 3. Optional OpenVINO probe
        if _openvino_importable() and not skip_openvino_probe:
            try:
                import openvino as ov
                core = ov.Core()
                ov_devs = list(core.available_devices)
                devices["openvino_devices"] = ov_devs
                devices["openvino_available"] = len(ov_devs) > 0
                if "NPU" in ov_devs:
                    devices["intel_npu"]["available"] = True
                    devices["intel_npu"]["status"] = "Active"
                    devices["intel_npu"]["backend"] = "OpenVINO Level Zero"
            except Exception as e:
                devices["openvino_probe_error"] = str(e)

        if apply_profile:
            devices["install_profile"] = load_install_profile()
            return apply_install_mask(devices, devices["install_profile"])
        return devices

    @property
    def primary_device_label(self) -> str:
        gpu = self.devices.get("gpu", {})
        if gpu.get("available"):
            return str(gpu.get("device_name", "GPU"))
        return str(self.devices.get("cpu", {}).get("device_name", "CPU"))

    @property
    def has_dedicated_gpu(self) -> bool:
        gpu = self.devices.get("gpu", {})
        return bool(gpu.get("available") and not gpu.get("is_integrated", False))

    @property
    def has_npu(self) -> bool:
        return bool(
            self.devices.get("intel_npu", {}).get("available")
            or self.devices.get("amd_npu", {}).get("available")
        )

    @property
    def cpu_threads(self) -> int:
        return int(self.devices.get("cpu", {}).get("threads", _LOGICAL_CORES))

    def preferred_coprocessor_target(self, heavy: bool = False) -> str:
        if self.devices.get("intel_npu", {}).get("available"):
            return "INTEL_NPU"
        if self.devices.get("amd_npu", {}).get("available"):
            return "AMD_NPU"
        if self.devices.get("gpu", {}).get("available"):
            return "GPU"
        return "CPU"

    # ------------------------------------------------------------------
    # Cross-platform detector API (parity with the Windows hardware layer).
    # Consumers (AI engine, UI badge, workload router) rely on these names.
    # ------------------------------------------------------------------
    @property
    def has_gpu(self) -> bool:
        return bool(self.devices.get("gpu", {}).get("available"))

    @property
    def gpu_name(self) -> str:
        return str(self.devices.get("gpu", {}).get("device_name", "GPU"))

    @property
    def gpu_vendor(self) -> str:
        return str(self.devices.get("gpu", {}).get("vendor", "Generic"))

    @property
    def has_dgpu(self) -> bool:
        gpu = self.devices.get("gpu", {})
        return bool(gpu.get("available") and not gpu.get("is_integrated", False))

    @property
    def has_igpu(self) -> bool:
        gpu = self.devices.get("gpu", {})
        return bool(gpu.get("available") and gpu.get("is_integrated", False))

    @property
    def dgpu_name(self) -> str:
        for gpu in self.devices.get("gpus", []):
            if not gpu.get("is_integrated", False):
                return str(gpu.get("name", "dGPU"))
        return self.gpu_name if self.has_dgpu else "dGPU"

    @property
    def igpu_name(self) -> str:
        for gpu in self.devices.get("gpus", []):
            if gpu.get("is_integrated", False):
                return str(gpu.get("name", "iGPU"))
        return "iGPU"

    @property
    def has_nvidia(self) -> bool:
        return any("nvidia" in str(g.get("vendor", "")).lower() for g in self.devices.get("gpus", []))

    @property
    def has_amd_gpu(self) -> bool:
        return any(
            "amd" in str(g.get("vendor", "")).lower() or "radeon" in str(g.get("vendor", "")).lower()
            for g in self.devices.get("gpus", [])
        )

    @property
    def has_intel_gpu(self) -> bool:
        return any("intel" in str(g.get("vendor", "")).lower() for g in self.devices.get("gpus", []))

    @property
    def npu_vendor(self) -> str:
        if self.devices.get("intel_npu", {}).get("available"):
            return "Intel"
        if self.devices.get("amd_npu", {}).get("available"):
            return "AMD"
        return "None"

    @property
    def npu_name(self) -> str:
        for key in ("intel_npu", "amd_npu"):
            if self.devices.get(key, {}).get("available"):
                return str(self.devices.get(key, {}).get("device_name", "NPU"))
        return "NPU"

    @property
    def npu_backend(self) -> str:
        for key in ("intel_npu", "amd_npu"):
            if self.devices.get(key, {}).get("available"):
                return str(self.devices.get(key, {}).get("backend", "None"))
        return "None"

    @property
    def is_intel_npu(self) -> bool:
        return bool(self.devices.get("intel_npu", {}).get("available"))

    @property
    def is_amd_npu(self) -> bool:
        return bool(self.devices.get("amd_npu", {}).get("available"))

    @property
    def cpu_name(self) -> str:
        return str(self.devices.get("cpu", {}).get("device_name", "CPU"))

    @property
    def install_profile(self) -> HardwareProfile | None:
        return self.devices.get("install_profile") or load_install_profile()

    @property
    def llama_wheel(self) -> str:
        profile = self.install_profile or {}
        return str(profile.get("llama_wheel", "cpu"))

    @property
    def coprocessor_kind(self) -> str:
        return self.preferred_coprocessor_target(heavy=False)

    def all_gpus_summary(self) -> str:
        gpus = self.devices.get("gpus", [])
        if not gpus:
            return "No GPU"
        return ", ".join(str(gpu.get("name", "GPU")) for gpu in gpus)

    def get_summary_string(self) -> str:
        parts = [self.cpu_name]
        if self.has_gpu:
            parts.append(self.gpu_name)
        if self.has_npu:
            parts.append(f"{self.npu_vendor} NPU")
        return " + ".join(parts)

    def get_live_summary_string(self) -> str:
        return self.get_summary_string()

    def get_routing_tooltip(self) -> str:
        return self.get_summary_string()

    def routing_standby_label(self) -> str:
        return standby_label(self.install_profile)


class HardwareRouter:
    """Computes routing profiles, acceleration tiers, and UI badges for Linux execution."""
    def __init__(self, detector: Optional[HardwareDetector] = None):
        self.detector = detector or HardwareDetector()

    def get_tier_info(self, is_heavy_workload: bool = False) -> Dict[str, Any]:
        devs = self.detector.devices
        gpu = devs.get("gpu", {})
        has_gpu = bool(gpu.get("available"))
        gpu_name = str(gpu.get("device_name", "GPU"))
        has_npu = self.detector.has_npu
        intel_npu = devs.get("intel_npu", {}).get("available")
        npu_vendor = "Intel" if intel_npu else ("AMD" if devs.get("amd_npu", {}).get("available") else "Generic")

        if has_npu and has_gpu:
            return {
                "tier_id": 3,
                "tier_name": f"{npu_vendor} NPU + {gpu_name} + CPU Turbo Mesh",
                "badge": f"⚡ {npu_vendor} NPU + {gpu_name} + CPU",
                "color": "#eab308",
                "bg_color": "#713f12",
                "strategy": f"{npu_vendor} NPU + {gpu_name} + CPU",
                "short_tag": "NPU + GPU + CPU",
                "coprocessor_target": self.detector.preferred_coprocessor_target(heavy=True),
                "hw_tag": f"*{npu_vendor} NPU + {gpu_name} + CPU*",
                "npu_vendor": npu_vendor,
                "mode": "heavy_mesh",
            }

        if has_npu:
            return {
                "tier_id": 1,
                "tier_name": f"Tier 1: {npu_vendor} NPU Dedicated Core",
                "badge": f"⚡ {npu_vendor} NPU Ambient Core",
                "color": "#10b981",
                "bg_color": "#064e3b",
                "strategy": f"{npu_vendor} NPU",
                "short_tag": "NPU",
                "coprocessor_target": self.detector.preferred_coprocessor_target(heavy=False),
                "hw_tag": f"*{npu_vendor} NPU*",
                "npu_vendor": npu_vendor,
                "mode": "default_npu",
            }

        if has_gpu:
            return {
                "tier_id": 2,
                "tier_name": f"Vulkan/CUDA GPU + CPU Mesh ({gpu_name})",
                "badge": f"⚡ {gpu_name} + CPU",
                "color": "#38bdf8",
                "bg_color": "#0c4a6e",
                "strategy": "GPU + CPU",
                "short_tag": "GPU + CPU",
                "coprocessor_target": self.detector.preferred_coprocessor_target(heavy=is_heavy_workload),
                "hw_tag": f"*{gpu_name} + CPU*",
                "npu_vendor": "None",
                "mode": "gpu_cpu_mesh",
            }

        return {
            "tier_id": 1,
            "tier_name": f"CPU Multi-Core Vector Mesh ({self.detector.cpu_threads}T)",
            "badge": f"⚡ CPU Multi-Core ({self.detector.cpu_threads}T)",
            "color": "#10b981",
            "bg_color": "#064e3b",
            "strategy": "CPU",
            "short_tag": "CPU",
            "coprocessor_target": "NONE",
            "hw_tag": "*CPU*",
            "npu_vendor": "None",
            "mode": "cpu_vector_mesh",
        }


class DynamicHardwareRouter(HardwareRouter):
    """
    Computes compute workload demand for A.U.R.A. and orchestrates heterogeneous
    multi-hardware scaling across NPU, iGPU, dGPU, and CPU mesh on Linux.

    Provides the ``hardware_plan`` contract (tier_id, tier_name, badge, colors,
    strategy, coprocessor_target, hw_tag, npu_vendor, mode) consumed by the UI,
    matching the Windows hardware layer.
    """

    def __init__(self, detector: Optional[HardwareDetector] = None):
        super().__init__(detector)

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 1
        # Fast character heuristic: ~4 chars per token for dense technical text.
        return max(1, len(text) // 4)

    def route_workload(
        self,
        token_count: int,
        has_image: bool = False,
        has_doc: bool = False,
        attachment_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Routes workload across the heterogeneous hardware mesh automatically:
          1. File / vision upload override -> engage all available compute units.
          2. Heavy tactical reasoning / D-Scan (token_count > 350) -> full mesh.
          3. Ambient / conversational queries -> energy-efficient NPU / primary GPU.
        """
        det = self.detector
        npu_vendor = det.npu_vendor
        has_npu = det.has_npu
        has_gpu = det.has_gpu
        has_dgpu = det.has_dgpu
        has_igpu = det.has_igpu
        gpu_name = det.gpu_name
        gpu_vendor = det.gpu_vendor
        gpu_label = gpu_strategy_label(det.install_profile, gpu_vendor)

        has_attachments = has_image or has_doc or attachment_count > 0
        is_heavy_workload = has_attachments or token_count > 350

        installed = set((det.install_profile or {}).get("profiles") or [])
        profile_locked = det.install_profile is not None
        quad_installed = False
        if profile_locked:
            has_npu_stack = "intel_npu" in installed or "amd_npu" in installed
            has_igpu_stack = "amd_igpu" in installed or "intel_igpu" in installed
            has_dgpu_stack = any(p in installed for p in ("nvidia_dgpu", "amd_dgpu", "intel_dgpu"))
            quad_installed = has_npu_stack and has_igpu_stack and has_dgpu_stack

        # TIER 4: Heterogeneous quad-mesh (NPU + iGPU + dGPU + CPU).
        if has_npu and has_dgpu and has_igpu and quad_installed:
            return {
                "tier_id": 4,
                "tier_name": f"Heterogeneous Quad-Mesh ({npu_vendor} NPU + {det.dgpu_name} + {det.igpu_name} + CPU)",
                "badge": f"⚡ Quad-Mesh: {npu_vendor} NPU + dGPU + iGPU + CPU",
                "color": "#f43f5e",
                "bg_color": "#4c0519",
                "strategy": f"{npu_vendor} NPU + dGPU + iGPU + CPU",
                "short_tag": "Quad-Mesh",
                "coprocessor_target": det.preferred_coprocessor_target(heavy=True),
                "hw_tag": f"*{npu_vendor} NPU + dGPU + iGPU + CPU*",
                "npu_vendor": npu_vendor,
                "mode": "quad_mesh",
            }

        # TIER 3 / 1: NPU present (Intel Core Ultra / AMD Ryzen AI).
        if has_npu and has_gpu:
            if is_heavy_workload:
                gpu_desc = gpu_label if not has_igpu else det.igpu_name
                return {
                    "tier_id": 3,
                    "tier_name": f"Full Compute Mesh ({npu_vendor} NPU + {gpu_desc} + CPU)",
                    "badge": f"⚡ Full Mesh: {npu_vendor} NPU + {gpu_desc} + CPU",
                    "color": "#f43f5e",
                    "bg_color": "#4c0519",
                    "strategy": f"{npu_vendor} NPU + {gpu_desc} + CPU",
                    "short_tag": "NPU + GPU + CPU",
                    "coprocessor_target": det.preferred_coprocessor_target(heavy=True),
                    "hw_tag": f"*{npu_vendor} NPU + {gpu_desc} + CPU*",
                    "npu_vendor": npu_vendor,
                    "mode": "heavy_mesh",
                }
            return {
                "tier_id": 1,
                "tier_name": f"Tier 1: {npu_vendor} NPU Dedicated Core",
                "badge": f"⚡ {npu_vendor} NPU Ambient Core",
                "color": "#10b981",
                "bg_color": "#064e3b",
                "strategy": f"{npu_vendor} NPU",
                "short_tag": "NPU",
                "coprocessor_target": det.preferred_coprocessor_target(heavy=False),
                "hw_tag": f"*{npu_vendor} NPU*",
                "npu_vendor": npu_vendor,
                "mode": "default_npu",
            }

        # TIER 2: GPU + CPU mesh.
        if has_gpu:
            return {
                "tier_id": 2,
                "tier_name": f"Vulkan/CUDA GPU + CPU Mesh ({gpu_name})",
                "badge": f"⚡ {gpu_name} + CPU",
                "color": "#38bdf8",
                "bg_color": "#0c4a6e",
                "strategy": "GPU + CPU",
                "short_tag": "GPU + CPU",
                "coprocessor_target": det.preferred_coprocessor_target(heavy=is_heavy_workload),
                "hw_tag": f"*{gpu_name} + CPU*",
                "npu_vendor": "None",
                "mode": "gpu_cpu_mesh",
            }

        # TIER 1: CPU multi-core vector mesh.
        return {
            "tier_id": 1,
            "tier_name": f"CPU Multi-Core Vector Mesh ({det.cpu_threads}T)",
            "badge": f"⚡ CPU Multi-Core ({det.cpu_threads}T)",
            "color": "#10b981",
            "bg_color": "#064e3b",
            "strategy": "CPU",
            "short_tag": "CPU",
            "coprocessor_target": "NONE",
            "hw_tag": "*CPU*",
            "npu_vendor": "None",
            "mode": "cpu_vector_mesh",
        }
