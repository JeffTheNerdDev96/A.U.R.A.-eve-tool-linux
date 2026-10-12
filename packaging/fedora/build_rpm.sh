#!/usr/bin/env bash
# ==============================================================================
# Adaptive Underworld Recon Array (A.U.R.A.) - Fedora / RHEL .rpm builder
# Copyright (C) 2026 JeffTheNerdDev96 | GNU Affero General Public License v3.0
# ==============================================================================
# Produces: dist/aura-eve-tool-<version>-<release>.noarch.rpm
# Requires: rpm-build, tar, gzip, sed.
#
# COPR: create a COPR project pointing at this repository and set the
# "Spec File" to packaging/fedora/aura-eve-tool.spec (COPR builds from git).
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
# v0.6.0-alpha.4 -> Version=0.6.0  Release=0.4.alpha
BASE="$(printf '%s' "${VER}" | sed -E 's/^v//; s/-alpha\./~alpha./; s/-/./g')"
RPMVER="${BASE%%~*}"
if [ "${BASE}" = "${RPMVER}" ]; then
    RPMREL="1"
else
    ALPHA_NUM="$(printf '%s' "${BASE}" | sed -E 's/.*alpha\.//')"
    RPMREL="0.${ALPHA_NUM}.alpha"
fi

TOP="${HERE}/rpmbuild"
rm -rf "${TOP}"
mkdir -p "${TOP}/SOURCES" "${TOP}/SPECS" "${TOP}/BUILD" "${TOP}/BUILDROOT" "${TOP}/RPMS" "${TOP}/SRPMS"

echo "==================================================================="
echo "  Building A.U.R.A. ${VER} (.rpm ${RPMVER}-${RPMREL})"
echo "  Topdir: ${TOP}"
echo "==================================================================="

# Build a source tarball of the whole repository root.
NAME="aura-eve-tool-${RPMVER}"
tar -C "${ROOT}" -czf "${TOP}/SOURCES/${NAME}.tar.gz" \
    --transform "s,^\./,${NAME}/," \
    --exclude='./.git' --exclude='./dist' --exclude='./packaging/ubuntu/build' \
    --exclude='./packaging/fedora/rpmbuild' --exclude='**/__pycache__' \
    .

# Stamp the version/release into the spec.
sed -e "s/^Version:.*/Version:        ${RPMVER}/" \
    -e "s/^Release:.*/Release:        ${RPMREL}%{?dist}/" \
    "${HERE}/aura-eve-tool.spec" > "${TOP}/SPECS/aura-eve-tool.spec"

echo "[1/2] Running rpmbuild..."
rpmbuild --define "_topdir ${TOP}" -bb "${TOP}/SPECS/aura-eve-tool.spec"

echo "[2/2] Collecting artifacts..."
mkdir -p "${ROOT}/dist"
shopt -s nullglob
for rpm in "${TOP}"/RPMS/noarch/*.rpm; do
    cp "${rpm}" "${ROOT}/dist/"
done
shopt -u nullglob

ls -l "${ROOT}/dist/" || true
echo "[OK] .rpm build complete."
