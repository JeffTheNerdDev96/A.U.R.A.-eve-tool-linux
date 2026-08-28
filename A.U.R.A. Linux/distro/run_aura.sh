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
# Native Linux Launcher for Adaptive Underworld Recon Array (A.U.R.A.) - v0.4.2-alpha.1
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export PYTHONDONTWRITEBYTECODE=1

echo "==================================================================="
echo "  [+] Adaptive Underworld Recon Array (A.U.R.A.) - v0.4.2-alpha.1"
echo "  Angel Cartel Cybernetics Division — Native Linux Release"
echo "==================================================================="
echo ""

# 1. Resolve Python 3.12+ interpreter
PYTHON_BIN=""

if [ -f "${APP_ROOT}/.venv/bin/python" ]; then
    PYTHON_BIN="${APP_ROOT}/.venv/bin/python"
elif [ -f "${APP_ROOT}/requirements/venv/bin/python" ]; then
    PYTHON_BIN="${APP_ROOT}/requirements/venv/bin/python"
elif [ -f "${APP_ROOT}/venv/bin/python" ]; then
    PYTHON_BIN="${APP_ROOT}/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
fi

if [ -z "${PYTHON_BIN}" ]; then
    echo "[X] Error: Python 3.12+ was not found on your system."
    echo "[!] Run '${SCRIPT_DIR}/setup_ubuntu.sh' to install required packages and create the environment."
    exit 1
fi

# 2. Configure Wayland / XCB display server fallback
if [ "${XDG_SESSION_TYPE}" = "wayland" ] || [ -n "${WAYLAND_DISPLAY}" ]; then
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland;xcb}"
else
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
fi

# 3. Configure shared libraries
export LD_LIBRARY_PATH="${APP_ROOT}/requirements/venv/lib/python3.12/site-packages/llama_cpp/lib:${LD_LIBRARY_PATH}"

echo "[+] Launching A.U.R.A. Native Interface..."
exec "${PYTHON_BIN}" "${APP_ROOT}/app.py" "$@"
