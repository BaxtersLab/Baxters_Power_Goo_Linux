#!/usr/bin/env python3
"""
Baxters Power Goo — Linux launcher
"""

import logging
import sys
from pathlib import Path

# Ensure the src/ directory next to this file is on the import path
_APP_DIR = Path(__file__).resolve().parent
_SRC_DIR = _APP_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
from baxters_power_goo.error_handler import setup_logging
from baxters_power_goo.xdg_paths import get_cache_dir, get_config_dir
from baxters_power_goo.clipboard_linux import is_clipboard_tool_available

_LOG_FILE = get_cache_dir() / "baxters_power_goo.log"
setup_logging(level=logging.INFO, log_file=str(_LOG_FILE))
logger = logging.getLogger(__name__)

# Pre-flight clipboard warning
if not is_clipboard_tool_available():
    logger.warning(
        "No clipboard tool detected (xclip / wl-paste).  "
        "Paste-from-clipboard will be disabled.  "
        "Install xclip (X11) or wl-clipboard (Wayland) to enable it."
    )

# ---------------------------------------------------------------------------
# Qt application bootstrap
# ---------------------------------------------------------------------------
from PyQt6.QtWidgets import QApplication

_ASSETS_DIR = Path(__file__).parent / "assets"
_ICON_PATH = _ASSETS_DIR / "icon_256.png"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Baxters Power Goo")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Baxter")

    from baxters_power_goo.gui.main_window import MainWindow
    window = MainWindow(icon_path=_ICON_PATH)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
