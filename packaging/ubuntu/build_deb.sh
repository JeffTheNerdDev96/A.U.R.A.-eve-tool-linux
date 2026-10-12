#!/usr/bin/env bash
# ==============================================================================
# Adaptive Underworld Recon Array (A.U.R.A.) - Ubuntu / Debian .deb builder
# Copyright (C) 2026 JeffTheNerdDev96 | GNU Affero General Public License v3.0
# ==============================================================================
# Produces: dist/aura-eve-tool_<version>_all.deb
# Requires: dpkg-dev, debhelper (>= 13). Run from anywhere; paths are resolved.
# ==============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
SRC="${ROOT}/A.U.R.A. Linux"

if [ ! -f "${SRC}/version.py" ]; then
    echo "[X] Source tree not found at: ${SRC}" >&2
    exit 1
fi

VER="$(grep -oP 'VERSION\s*=\s*"\K[^"]+' "${SRC}/version.py")"
# v0.6.0-alpha.4 -> 0.6.0~alpha.4 (Debian sorts ~alpha below the final release)
DEB_VER="$(printf '%s' "${VER}" | sed -E 's/^v//; s/-alpha\./~alpha./; s/-/./g')"

STAGE="${HERE}/build/aura-eve-tool-${DEB_VER}"
rm -rf "${HERE}/build"
mkdir -p "${STAGE}/debian" "${STAGE}/packaging/common"

echo "==================================================================="
echo "  Building A.U.R.A. ${VER} (.deb ${DEB_VER})"
echo "  Staging: ${STAGE}"
echo "==================================================================="

cp -a "${SRC}" "${STAGE}/aura"
cp -a "${HERE}/debian/." "${STAGE}/debian/"
cp -a "${ROOT}/packaging/common/." "${STAGE}/packaging/common/"
for f in README.md CHANGELOG.md LICENSE; do
    [ -f "${ROOT}/${f}" ] && cp -a "${ROOT}/${f}" "${STAGE}/${f}"
done

sed -i "1s/.*/aura-eve-tool (${DEB_VER}) unstable; urgency=medium/" "${STAGE}/debian/changelog"

chmod +x "${STAGE}/debian/rules" "${STAGE}/debian/postinst" "${STAGE}/debian/prerm"

echo "[1/2] Running dpkg-buildpackage..."
( cd "${STAGE}" && dpkg-buildpackage -us -uc -b -d )

echo "[2/2] Collecting artifacts..."
mkdir -p "${ROOT}/dist"
shopt -s nullglob
for deb in "${HERE}/build/"*.deb; do
    cp "${deb}" "${ROOT}/dist/"
done
shopt -u nullglob

ls -l "${ROOT}/dist/" || true
echo "[OK] .deb build complete."
