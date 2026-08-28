#!/usr/bin/env bash
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
# Hardware Acceleration Setup for Linux (Vulkan / CUDA / CPU)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENV_PIP="${APP_ROOT}/.venv/bin/pip"
if [ ! -f "${VENV_PIP}" ]; then
    VENV_PIP="${APP_ROOT}/requirements/venv/bin/pip"
fi

if [ ! -f "${VENV_PIP}" ]; then
    echo "[X] Error: Virtual environment not found. Please run '${SCRIPT_DIR}/setup_ubuntu.sh' first."
    exit 1
fi

echo "==================================================================="
echo "  [+] A.U.R.A. Hardware Acceleration Selector (Linux)"
echo "==================================================================="
echo "1) Vulkan Compute (Recommended: AMD Radeon RADV, Intel Arc, NVIDIA)"
echo "2) NVIDIA CUDA 12.x (GeForce RTX / Quadro with proprietary driver)"
echo "3) Multi-Core CPU Vector Mesh (AVX2 / AVX-512 SIMD)"
echo ""
read -p "Select acceleration profile [1-3] (Default 1): " choice
choice="${choice:-1}"

case "${choice}" in
    1)
        echo "[+] Installing Vulkan acceleration packages..."
        "${VENV_PIP}" install -r "${APP_ROOT}/requirements/requirements-vulkan.txt"
        ;;
    2)
        echo "[+] Installing NVIDIA CUDA packages..."
        "${VENV_PIP}" install -r "${APP_ROOT}/requirements/requirements-cuda.txt"
        ;;
    3)
        echo "[+] Configuring CPU Vector Mesh mode..."
        "${VENV_PIP}" install -r "${APP_ROOT}/requirements/requirements.txt"
        ;;
    *)
        echo "[X] Invalid selection. Defaulting to Vulkan Compute."
        "${VENV_PIP}" install -r "${APP_ROOT}/requirements/requirements-vulkan.txt"
        ;;
esac

echo ""
echo "[SUCCESS] Hardware acceleration profile installed successfully!"
