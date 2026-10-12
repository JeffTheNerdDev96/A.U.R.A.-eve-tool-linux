#!/usr/bin/env bash
# ==============================================================================
# Adaptive Underworld Recon Array (A.U.R.A.) - Optional LLM / VOIP provisioner
# Copyright (C) 2026 JeffTheNerdDev96 | GNU Affero General Public License v3.0
# ==============================================================================
# The distro packages declare only the pure-Python / system dependencies.
# llama-cpp-python (local GGUF inference) and the Mumble VOIP stack are not
# packaged by every distribution, so this helper builds an isolated virtual
# environment at /opt/aura/.venv which the 'aura' launcher prefers when present.
#
#   sudo ./aura-llm-setup.sh           # CPU build (portable default)
#   sudo ./aura-llm-setup.sh vulkan    # AMD RADV / Intel ANV / NVIDIA Vulkan
#   sudo ./aura-llm-setup.sh cuda      # NVIDIA CUDA 12.x
# ==============================================================================
set -euo pipefail

APP_ROOT="${AURA_APP_ROOT:-/opt/aura}"
BACKEND="${1:-cpu}"
VENV="${APP_ROOT}/.venv"

echo "==================================================================="
echo "  A.U.R.A. LLM / VOIP provisioner (backend: ${BACKEND})"
echo "  Target venv: ${VENV}"
echo "==================================================================="

PY="$(command -v python3)"
if [ ! -x "${PY}" ]; then
    echo "[X] python3 was not found. Install your distribution's python3 package." >&2
    exit 1
fi

"${PY}" -m venv "${VENV}"
VPY="${VENV}/bin/python"
"${VPY}" -m pip install --upgrade pip setuptools wheel

echo "[+] Installing base + VOIP dependencies..."
if [ -f "${APP_ROOT}/requirements/requirements-voip.txt" ]; then
    "${VPY}" -m pip install -r "${APP_ROOT}/requirements/requirements-voip.txt"
else
    "${VPY}" -m pip install -r "${APP_ROOT}/requirements/requirements.txt"
    "${VPY}" -m pip install "pymumble==1.6.1" "opuslib==3.0.1"
fi

case "${BACKEND}" in
    vulkan)
        echo "[+] Building llama-cpp-python with Vulkan backend (this may take a while)..."
        CMAKE_ARGS="-DGGML_VULKAN=on" "${VPY}" -m pip install --no-binary llama-cpp-python "llama-cpp-python>=0.3.7"
        ;;
    cuda)
        echo "[+] Building llama-cpp-python with CUDA backend (this may take a while)..."
        CMAKE_ARGS="-DGGML_CUDA=on" "${VPY}" -m pip install --no-binary llama-cpp-python "llama-cpp-python>=0.3.7"
        ;;
    *)
        echo "[+] Installing portable CPU llama-cpp-python wheel..."
        "${VPY}" -m pip install "llama-cpp-python>=0.3.7"
        ;;
esac

if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    chown -R "${SUDO_USER}:${SUDO_USER}" "${VENV}" || true
fi

echo ""
echo "[OK] LLM / VOIP environment ready. Launch with: aura"
