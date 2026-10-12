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
Canonical Path Resolver for Adaptive Underworld Recon Array (A.U.R.A.) - Cross-Platform.
Single source of truth for app root, models, map data, logs, assets, and runtime paths.
  - Linux: FreeDesktop XDG Base Directory (XDG_DATA_HOME / XDG_CONFIG_HOME / XDG_CACHE_HOME)
    plus native hierarchies (/opt/aura, /usr/share/aura, /usr/local/share/aura).
  - Windows: %LOCALAPPDATA% / %APPDATA% and Program Files.
Environment overrides: AURA_DATA_DIR, AURA_CONFIG_DIR, AURA_CACHE_DIR, AURA_LOG_DIR,
AURA_MODEL_DIR.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

_IS_WIN = sys.platform == "win32"


def _ensure_dir(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def _env_override(name: str) -> Optional[str]:
    value = (os.environ.get(name) or "").strip()
    return value or None


def get_xdg_data_home() -> str:
    """Per-user data directory (~/.local/share/aura or %LOCALAPPDATA%\\aura)."""
    override = _env_override("AURA_DATA_DIR")
    if override:
        return _ensure_dir(override)
    if _IS_WIN:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return _ensure_dir(os.path.join(base, "aura"))


def get_xdg_config_home() -> str:
    """Per-user configuration directory (~/.config/aura or %APPDATA%\\aura)."""
    override = _env_override("AURA_CONFIG_DIR")
    if override:
        return _ensure_dir(override)
    if _IS_WIN:
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return _ensure_dir(os.path.join(base, "aura"))


def get_xdg_cache_home() -> str:
    """Per-user cache directory (~/.cache/aura or %LOCALAPPDATA%\\aura\\cache)."""
    override = _env_override("AURA_CACHE_DIR")
    if override:
        return _ensure_dir(override)
    if _IS_WIN:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return _ensure_dir(os.path.join(base, "aura"))


def get_app_root() -> str:
    """
    Returns the absolute path to the application root directory.
    - Frozen (PyInstaller): sys._MEIPASS or the executable directory.
    - From source: the parent of this 'core' package.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and os.path.isdir(meipass):
        return os.path.abspath(meipass)
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    this_file = os.path.abspath(__file__)
    core_dir = os.path.dirname(this_file)
    return os.path.dirname(core_dir)


def get_config_dir() -> str:
    """Returns the per-user configuration directory."""
    return get_xdg_config_home()


def get_models_dir(model_folder: str = "phi-4-mini") -> str:
    """Returns the model directory, preferring a bundled/app-local copy."""
    override = _env_override("AURA_MODEL_DIR")
    if override:
        return override
    local_models = os.path.join(get_app_root(), "models", model_folder)
    if os.path.isdir(local_models) or _IS_WIN:
        return local_models
    return _ensure_dir(os.path.join(get_xdg_data_home(), "models", model_folder))


def get_data_dir() -> str:
    """Returns the bundled data directory path."""
    return os.path.join(get_app_root(), "data")


def get_logs_dir() -> str:
    """Returns the logs directory (per-user data home), ensuring it exists."""
    override = _env_override("AURA_LOG_DIR")
    if override:
        return _ensure_dir(override)
    log_dir = os.path.join(get_xdg_data_home(), "logs")
    if _ensure_dir(log_dir) and os.path.isdir(log_dir):
        return log_dir
    return _ensure_dir(os.path.join(get_app_root(), "logs"))


def get_assets_dir() -> str:
    """Returns the assets directory path."""
    return os.path.join(get_app_root(), "assets")


def get_bootstrap_dir() -> str:
    """Returns the bootstrap directory path."""
    return os.path.join(get_app_root(), "bootstrap")


def find_model_path(model_folder: str = "phi-4-mini", model_file: str = "model_q4.gguf") -> Optional[str]:
    """
    Scans candidate locations for GGUF model weights across Linux XDG, native
    hierarchies, Windows user installs, and PyInstaller bundles.
    """
    app_root = get_app_root()
    home = os.path.expanduser("~")
    data_home = get_xdg_data_home()
    exe_dir = os.path.dirname(sys.executable)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    override = _env_override("AURA_MODEL_DIR")

    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "models", model_folder, model_file))
    if override:
        candidates.append(os.path.join(override, model_folder, model_file))
        candidates.append(os.path.join(override, model_file))
    candidates.extend([
        os.path.join(app_root, "models", model_folder, model_file),
        os.path.join(exe_dir, "models", model_folder, model_file),
        os.path.join(os.path.dirname(exe_dir), "models", model_folder, model_file),
        os.path.join(app_root, "..", "models", model_folder, model_file),
        os.path.join(data_home, "models", model_folder, model_file),
        os.path.join(home, ".local", "share", "aura", "models", model_folder, model_file),
        os.path.join("/opt", "aura", "models", model_folder, model_file),
        os.path.join("/usr", "share", "aura", "models", model_folder, model_file),
        os.path.join("/usr", "local", "share", "aura", "models", model_folder, model_file),
        os.path.join(local_app_data, "Programs", "A.U.R.A.", "models", model_folder, model_file),
    ])
    if _IS_WIN:
        candidates.append(os.path.join(r"C:\Program Files", "A.U.R.A.", "models", model_folder, model_file))

    for path in candidates:
        if path and os.path.isfile(path) and os.path.getsize(path) > 1_000_000:
            return os.path.abspath(path)
    return None
