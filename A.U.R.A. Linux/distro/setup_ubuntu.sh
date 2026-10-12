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
# Native Ubuntu Setup & Dependency Installer for A.U.R.A. - v0.6.0-alpha.4
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==================================================================="
echo "  [+] A.U.R.A. Ubuntu Environment & Dependency Setup"
echo "  Target: Ubuntu 22.04 / 24.04 LTS (Debian/Mint Compatible)"
echo "==================================================================="
echo ""

# 1. System packages check & install
echo "[1/4] Checking and installing required system packages via apt..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y \
        python3 \
        python3-venv \
        python3-pip \
        libgl1-mesa-glx \
        libegl1 \
        libvulkan1 \
        vulkan-tools \
        mesa-vulkan-drivers \
        tesseract-ocr \
        tesseract-ocr-eng
else
    echo "[!] Non-apt distribution detected. Please ensure Python 3.12+, Vulkan, and Tesseract are installed."
fi

# 2. Virtual environment creation
echo ""
echo "[2/4] Initializing Python virtual environment in '${APP_ROOT}/.venv'..."
python3 -m venv "${APP_ROOT}/.venv"
VENV_PYTHON="${APP_ROOT}/.venv/bin/python"
VENV_PIP="${APP_ROOT}/.venv/bin/pip"

# 3. Upgrade pip and install base requirements
echo ""
echo "[3/4] Installing Python application dependencies..."
"${VENV_PIP}" install --upgrade pip setuptools wheel
"${VENV_PIP}" install -r "${APP_ROOT}/requirements/requirements.txt"

# 4. Create desktop shortcut
echo ""
echo "[4/4] Configuring FreeDesktop launcher..."
DESKTOP_DIR="${HOME}/.local/share/applications"
mkdir -p "${DESKTOP_DIR}"
sed -e "s|{{APP_ROOT}}|${APP_ROOT}|g" "${SCRIPT_DIR}/aura.desktop" > "${DESKTOP_DIR}/aura.desktop"
chmod +x "${DESKTOP_DIR}/aura.desktop"
chmod +x "${SCRIPT_DIR}/run_aura.sh"

echo ""
echo "==================================================================="
echo "  [SUCCESS] A.U.R.A. Ubuntu Setup Complete!"
echo "  To launch: ${SCRIPT_DIR}/run_aura.sh"
echo "  Or select 'Adaptive Underworld Recon Array' from your Application Menu."
echo "==================================================================="
