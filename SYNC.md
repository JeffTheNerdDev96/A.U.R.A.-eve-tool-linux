# A.U.R.A. Linux — Synchronization & Parity Ledger

This document records the feature-parity baseline between the Windows master
repository and this native Linux repository, plus the dual-distro packaging
strategy.

- **Windows master:** `https://github.com/JeffTheNerdDev96/A.U.R.A-eve-tool`
- **Windows parity baseline commit:** `9d1953e` (`v0.6.0-alpha.4`)
- **Linux repo:** `https://github.com/JeffTheNerdDev96/A.U.R.A.-eve-tool-linux`
- **Sync branch:** `sync/v0.6.0-parity`
- **License:** GNU Affero General Public License v3.0 (AGPL-3.0)

## Packaging model

Source + **system distribution dependencies**, installed to `/opt/aura`:

- `/opt/aura/`           — application source tree
- `/usr/bin/aura`        — launcher shim (Wayland/xcb aware)
- `/usr/share/applications/aura.desktop`
- `~/.local/share/aura/` — runtime state (logs, models) per XDG Base Directory

Two independent pipelines live under `packaging/`:

- `packaging/ubuntu/` — Debian source package (`debian/` + `build_deb.sh`)
- `packaging/fedora/` — RPM spec (`aura-eve-tool.spec` + `build_rpm.sh`)
- `packaging/common/` — shared `aura.desktop.in`, launcher, man page

An optional helper `packaging/common/aura-llm-setup.sh` provisions
`llama-cpp-python` (and Mumble VOIP deps) into `/opt/aura/.venv`, which the
launcher prefers when present.

## Cross-platform contract

`core/paths.py` is the single source of truth and branches on `sys.platform`:
XDG directories on Linux, `%LOCALAPPDATA%`/Program Files on Windows. Environment
overrides: `AURA_DATA_DIR`, `AURA_CONFIG_DIR`, `AURA_CACHE_DIR`, `AURA_LOG_DIR`,
`AURA_MODEL_DIR`.

## Completed in this sync

### Launch blockers fixed
- `bootstrap/__init__.py` re-exported the real Linux symbols (was importing
  Windows-only `configure_qt_paths`/`probe_llama_backend`); added
  `configure_qt_paths`/`configure_frozen_qt_paths` to `bootstrap_runtime.py`.
- `subsystems/ai/engine.py` now probes `libllama.so`/`libllama.dylib` (was
  hard-coded to `llama.dll`) via platform-aware helpers.
- `app.py` crash logs now route through `core.paths.get_logs_dir()` (XDG).
- Base `requirements.txt` gained `numpy` and `llama-cpp-python`.
- `distro/run_aura.sh` resolves `llama_cpp/lib` dynamically (no `python3.12` hard-code).
- Removed the Windows-only `winocr` OCR fallback and credits; Tesseract is the
  sole Linux vision backend.

### Hardware layer repaired (was incomplete in the fork)
- `hardware/detector.py` never defined `DynamicHardwareRouter` (the fork renamed
  it to `HardwareRouter` without the `estimate_tokens`/`route_workload` API that
  `engine.py` calls) and lacked the `has_gpu`/`gpu_name`/`gpu_vendor`/`has_dgpu`/
  `has_igpu`/`dgpu_name`/`igpu_name`/`npu_vendor`/`llama_wheel`/
  `get_summary_string`/`install_profile` surface the UI reads.
  Added the full cross-platform detector API and a `DynamicHardwareRouter`.
- `scan_devices()` called `apply_install_mask(devices)` with a missing argument;
  now passes and caches `devices["install_profile"]` (matches Windows).

### Feature parity ported from Windows v0.6.0-alpha.4
- New datasets: `core/eve_modules_data.py`, `core/eve_ships_data.py`
- Fitting maths: `subsystems/fitting/dogma.py`
- New subsystem: `subsystems/dscan/` (models/parser/service)
- New subsystem: `subsystems/voip_mumble/` (models/runtime/client/service/audio),
  adapted to link system `libopus` on Linux
- New UI tab: `ui/tabs/dscan_tab.py`; `ui/tabs/voip_tab.py`
- Merged superset UI/core files: `ui/app_window.py`, `ui/theme.py`,
  `ui/__init__.py`, `ui/tabs/__init__.py`, `core/events.py`, and the grouped
  `subsystems/{fitting,fleet_comp,intel,map,wormhole,xmpp_chat}` modules
- `core/config.py` gained the VOIP settings block (kept `desktop_alerts_enabled`)
- Docs + `.github/` templates + `tools/tests` ported

## Verification evidence (Windows host, Python 3.14, PyQt6 6.11)
- `python -m compileall "A.U.R.A. Linux"` → clean (0 syntax errors)
- Static cross-module import checker → all `from … import` resolve
- Runtime import of `app`, `ui.app_window`, `ui.tabs.dscan_tab`,
  `ui.tabs.voip_tab`, `subsystems.voip_mumble.runtime` → OK
- `tools/run_all_tests.py`:
  - `test_codebase_integrity.py` → `OK (skipped=5)` (skips are Windows-only
    packaging internals, auto-detected by module availability)
  - `test_all_subsystems.py` → ALL PASSED (incl. DScanSubsystem, VOIPMumbleSubsystem)
  - `test_ui_integration.py` → ALL PASSED (incl. DScanTabWidget, VOIPTabWidget)
  - `test_lifecycle_and_memory.py`, `test_feed_filter.py`,
    `test_fitting_dogma.py`, `test_fleet_comp_parse.py`,
    `test_map_intel_expiration.py` → PASSED

## Notes / follow-ups
- The `packaging/*/build_*.sh`, `debian/rules`, and `aura-eve-tool.spec` are
  validated by CI (Ubuntu 24.04 + Fedora container); they cannot be executed on
  a Windows dev host.
- Renaming the source directory `A.U.R.A. Linux/` to a space-free name would
  simplify future packaging but was intentionally left unchanged.

