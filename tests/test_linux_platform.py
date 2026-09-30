"""
tests/test_linux_platform.py
Linux-specific tests for xdg_paths, clipboard_linux, and .desktop file.
"""

import os
import sys
import json
import stat
import subprocess
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

PROJECT_ROOT = Path(__file__).parent.parent


def _frozen_build(pkg: str):
    """Under `baxters-gate.sh --frozen`: the build of `pkg` that build-package.sh
    published from THIS repository's frozen commit (BAXTERS_BUILDS, filtered by
    the Baxters-Source-Commit the freeze names). None outside the frozen gate.
    Inside it, a missing build is a FAILURE, never a skip (2026-09-28): the
    pristine checkout the gate tests has no dist/."""
    builds, frozen = os.environ.get("BAXTERS_BUILDS"), os.environ.get("BAXTERS_FROZEN")
    if not (builds and frozen):
        return None
    rows = [l.split("|") for l in Path(frozen).read_text().splitlines() if l and not l.startswith("#")]
    repo = {r[1]: r[2] for r in rows if r[0] == "repo"}
    want = next((repo[r[2]] for r in rows if r[0] == "package" and r[1] == pkg), None)
    if want is None:
        pytest.fail(f"{pkg} is not a package in the freeze {frozen}")
    for d in sorted((Path(builds) / pkg).glob(f"{pkg}_*.deb")):
        got = subprocess.run(["dpkg-deb", "-f", str(d), "Baxters-Source-Commit"],
                             capture_output=True, text=True).stdout.strip()
        if got == want:
            return d
    pytest.fail(f"no build of {pkg} from {want[:12]} in {builds}")


# ---------------------------------------------------------------------------
# xdg_paths
# ---------------------------------------------------------------------------

class TestXdgPaths:
    def test_get_cache_dir_returns_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        # Re-import to pick up monkeypatched env
        import importlib, baxters_power_goo.xdg_paths as xdg
        importlib.reload(xdg)
        d = xdg.get_cache_dir()
        assert isinstance(d, Path)
        assert d.is_dir()

    def test_get_config_dir_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        import importlib, baxters_power_goo.xdg_paths as xdg
        importlib.reload(xdg)
        d = xdg.get_config_dir()
        assert d.is_dir()

    def test_get_data_dir_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        import importlib, baxters_power_goo.xdg_paths as xdg
        importlib.reload(xdg)
        d = xdg.get_data_dir()
        assert d.is_dir()

    def test_recent_files_path_inside_data_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        import importlib, baxters_power_goo.xdg_paths as xdg
        importlib.reload(xdg)
        p = xdg.get_recent_files_path()
        assert p.name == "recent_files.json"
        assert "baxters-power-goo" in str(p)

    def test_no_xdg_env_uses_defaults(self, monkeypatch):
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        import importlib, baxters_power_goo.xdg_paths as xdg
        importlib.reload(xdg)
        cache = xdg.get_cache_dir()
        assert ".cache" in str(cache) or str(Path.home()) in str(cache)


# ---------------------------------------------------------------------------
# clipboard_linux
# ---------------------------------------------------------------------------

class TestClipboardLinux:
    def test_detect_display_server_returns_string(self):
        from baxters_power_goo.clipboard_linux import detect_display_server
        result = detect_display_server()
        assert result in ("x11", "wayland", "unknown")

    def test_is_clipboard_tool_available_is_bool(self):
        from baxters_power_goo.clipboard_linux import is_clipboard_tool_available
        result = is_clipboard_tool_available()
        assert isinstance(result, bool)

    def test_paste_image_returns_none_on_no_tool(self, monkeypatch):
        from baxters_power_goo.clipboard_linux import detect_display_server
        import baxters_power_goo.clipboard_linux as cl
        import shutil

        # Force X11 path and hide xclip
        monkeypatch.setattr(cl, "detect_display_server", lambda: "x11")
        monkeypatch.setattr(shutil, "which", lambda _: None)

        result = cl.paste_image_from_clipboard()
        assert result is None

    def test_paste_image_returns_pil_image_or_none(self):
        """Result must be a PIL Image or None — never raises."""
        from baxters_power_goo import clipboard_linux as cl
        from PIL import Image
        result = cl.paste_image_from_clipboard()
        assert result is None or isinstance(result, Image.Image)

    def test_wayland_path_probe(self, monkeypatch):
        import baxters_power_goo.clipboard_linux as cl
        import shutil
        monkeypatch.setattr(cl, "detect_display_server", lambda: "wayland")
        monkeypatch.setattr(shutil, "which", lambda _: None)
        result = cl.paste_image_from_clipboard()
        assert result is None


# ---------------------------------------------------------------------------
# .desktop file
# ---------------------------------------------------------------------------

class TestDesktopFile:
    DESKTOP = PROJECT_ROOT / "debian" / "baxters-power-goo.desktop"

    def test_desktop_file_exists(self):
        assert self.DESKTOP.is_file(), f"Missing: {self.DESKTOP}"

    def test_required_keys_present(self):
        content = self.DESKTOP.read_text()
        for key in ("Type=Application", "Name=", "Exec=", "Icon=", "Categories="):
            assert key in content, f"Missing key: {key}"

    def test_exec_uses_correct_command(self):
        content = self.DESKTOP.read_text()
        assert "baxters-power-goo" in content

    def test_icon_name_matches_package(self):
        content = self.DESKTOP.read_text()
        assert "Icon=baxters-power-goo" in content


# ---------------------------------------------------------------------------
# Packaging artefacts
# ---------------------------------------------------------------------------

def _power_goo_deb():
    """The package under test: the frozen build under the frozen gate; elsewhere
    the dist/ build of the version packaging/DEBIAN/control declares NOW. (It was
    a hardcoded 1.0.0 file name, satisfied for weeks by a stale 1.0.0 .deb left in
    dist/ while the package was already 1.0.0-3. 2026-09-28.)"""
    deb = _frozen_build("baxters-power-goo")
    if deb is not None:
        return deb
    ver = next(l.split(": ", 1)[1].strip() for l in
               (PROJECT_ROOT / "packaging" / "DEBIAN" / "control").read_text().splitlines()
               if l.startswith("Version: "))
    deb = PROJECT_ROOT / "dist" / f"baxters-power-goo_{ver}_all.deb"
    if not deb.is_file():
        pytest.skip(f"no build of the current version {ver} in dist/; the frozen gate checks the published build")
    return deb


class TestPackagingArtefacts:
    def test_deb_file_exists(self):
        deb = _power_goo_deb()
        assert deb.is_file(), f"Missing .deb: {deb}"

    def test_deb_is_non_empty(self):
        assert _power_goo_deb().stat().st_size > 1000

    def test_postinst_is_executable(self):
        postinst = PROJECT_ROOT / "debian" / "DEBIAN" / "postinst"
        assert postinst.is_file()
        mode = postinst.stat().st_mode
        assert bool(mode & stat.S_IXUSR), "postinst not executable"

    def test_control_has_depends(self):
        control = PROJECT_ROOT / "debian" / "DEBIAN" / "control"
        assert "Depends:" in control.read_text()

    def test_four_icon_sizes_staged(self):
        for size in ("16x16", "32x32", "48x48", "256x256"):
            p = PROJECT_ROOT / "debian" / "icons" / "hicolor" / size / "apps" / "baxters-power-goo.png"
            assert p.is_file(), f"Missing icon: {p}"

    def test_launcher_script_is_executable(self):
        launcher = PROJECT_ROOT / "scripts" / "baxters-power-goo"
        assert launcher.is_file()
        mode = launcher.stat().st_mode
        assert bool(mode & stat.S_IXUSR), "launcher not executable"
