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
A.U.R.A. Master Test Runner
Executes all unit, integration, subsystem, headless UI, and integrity test suites.
"""

import os
import sys
import subprocess

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_ROOT = os.path.dirname(_THIS_DIR) if os.path.basename(_THIS_DIR) == "tools" else _THIS_DIR
_PYTHON_EXE = sys.executable

TEST_SCRIPTS = [
    os.path.join(_THIS_DIR, "tests", "test_codebase_integrity.py"),
    os.path.join(_THIS_DIR, "tests", "test_all_subsystems.py"),
    os.path.join(_THIS_DIR, "tests", "test_ui_integration.py"),
    os.path.join(_THIS_DIR, "tests", "test_lifecycle_and_memory.py"),
    os.path.join(_THIS_DIR, "tests", "test_fitting_dogma.py"),
    os.path.join(_THIS_DIR, "tests", "test_fleet_comp_parse.py"),
    os.path.join(_THIS_DIR, "tests", "test_feed_filter.py"),
    os.path.join(_THIS_DIR, "tests", "test_map_intel_expiration.py"),
]


def main() -> int:
    print("=" * 70)
    print("   RUNNING A.U.R.A. AUTOMATED TEST & VERIFICATION SUITE")
    print("=" * 70)

    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = _APP_ROOT + (os.pathsep + existing_pp if existing_pp else "")

    failed = 0
    passed = 0

    for script in TEST_SCRIPTS:
        name = os.path.relpath(script, _APP_ROOT)
        if not os.path.isfile(script):
            print(f" -> [SKIPPED] {name} (script not present)")
            continue
        try:
            res = subprocess.run([_PYTHON_EXE, script], cwd=_APP_ROOT, env=env, timeout=120)
            if res.returncode == 0:
                passed += 1
                print(f" -> [PASSED] {name}")
            else:
                failed += 1
                print(f" -> [FAILED] {name} (Exit code: {res.returncode})")
        except subprocess.TimeoutExpired:
            failed += 1
            print(f" -> [FAILED] {name} (Timed out after 120s)")

    print("\n" + "=" * 70)
    if failed == 0:
        print(f" [ALL PASSED] {passed}/{passed} TEST SUITES COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        return 0
    else:
        print(f" [FAILURES DETECTED] {passed} passed, {failed} failed.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
