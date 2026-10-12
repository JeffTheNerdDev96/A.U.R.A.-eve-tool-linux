#!/usr/bin/env bash
# ==============================================================================
# Adaptive Underworld Recon Array (A.U.R.A.) - dual-distro build orchestrator
# Copyright (C) 2026 JeffTheNerdDev96 | GNU Affero General Public License v3.0
# ==============================================================================
# Builds the Ubuntu/Debian .deb and/or the Fedora .rpm into ./dist.
#
#   ./packaging/build_all.sh          # build whatever the host supports
#   ./packaging/build_all.sh deb      # .deb only
#   ./packaging/build_all.sh rpm      # .rpm only
# ==============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-all}"

have() { command -v "$1" >/dev/null 2>&1; }

build_deb() {
    if have dpkg-buildpackage && have dpkg -s debhelper >/dev/null 2>&1; then
        echo ">>> Building Debian/Ubuntu .deb ..."
        bash "${HERE}/ubuntu/build_deb.sh"
    else
        echo "[!] Skipping .deb: dpkg-buildpackage / debhelper not present."
    fi
}

build_rpm() {
    if have rpmbuild; then
        echo ">>> Building Fedora/RHEL .rpm ..."
        bash "${HERE}/fedora/build_rpm.sh"
    else
        echo "[!] Skipping .rpm: rpmbuild not present."
    fi
}

case "${TARGET}" in
    deb) build_deb ;;
    rpm) build_rpm ;;
    all) build_deb; build_rpm ;;
    *) echo "Usage: $0 [all|deb|rpm]" >&2; exit 2 ;;
esac

echo ""
echo "===== dist ====="
ls -l "${HERE}/../dist" 2>/dev/null || echo "(no artifacts produced)"
