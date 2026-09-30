#!/usr/bin/env python3
"""
XDG Base-Directory helpers — Linux only.
Provides cache, config, data, and recent-files paths that respect
the XDG Base Directory Specification (freedesktop.org/wiki/Spec…).
"""

import os
from pathlib import Path

_HOME = Path.home()

APP_NAME = "baxters-power-goo"


def get_cache_dir() -> Path:
    """~/.cache/baxters-power-goo  (or $XDG_CACHE_HOME/…)"""
    base = Path(os.environ.get("XDG_CACHE_HOME", "") or _HOME / ".cache")
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_config_dir() -> Path:
    """~/.config/baxters-power-goo  (or $XDG_CONFIG_HOME/…)"""
    base = Path(os.environ.get("XDG_CONFIG_HOME", "") or _HOME / ".config")
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_data_dir() -> Path:
    """~/.local/share/baxters-power-goo  (or $XDG_DATA_HOME/…)"""
    base = Path(os.environ.get("XDG_DATA_HOME", "") or _HOME / ".local" / "share")
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_recent_files_path() -> Path:
    """Path to the recent-files JSON list inside the data directory."""
    return get_data_dir() / "recent_files.json"
