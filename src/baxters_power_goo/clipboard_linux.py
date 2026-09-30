#!/usr/bin/env python3
"""
Linux clipboard helper — Baxters Power Goo.
Reads image data from the X11 or Wayland clipboard using
`xclip` (X11) or `wl-paste` (Wayland).  Returns a PIL RGBA Image
or None if no image is on the clipboard or no tool is available.
"""

import io
import os
import shutil
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def detect_display_server() -> str:
    """
    Return 'wayland', 'x11', or 'unknown'.
    Checks $XDG_SESSION_TYPE then $WAYLAND_DISPLAY.
    """
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "wayland":
        return "wayland"
    if session_type == "x11":
        return "x11"
    # Fallback: WAYLAND_DISPLAY presence
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    return "x11"  # assume X11 if nothing else indicates


def is_clipboard_tool_available() -> bool:
    """Return True if xclip or wl-paste is on PATH."""
    server = detect_display_server()
    if server == "wayland":
        return shutil.which("wl-paste") is not None
    return shutil.which("xclip") is not None


def paste_image_from_clipboard() -> Optional["PIL.Image.Image"]:  # type: ignore[name-defined]
    """
    Grab the current clipboard image.

    Returns a PIL RGBA Image, or None when:
    - no image is on the clipboard
    - the required external tool is missing
    - an error occurs
    """
    try:
        from PIL import Image  # local import — avoids hard dep at module level
    except ImportError:
        logger.error("Pillow is not installed; cannot read clipboard.")
        return None

    server = detect_display_server()

    try:
        if server == "wayland":
            if not shutil.which("wl-paste"):
                logger.debug("wl-paste not found; clipboard unavailable on Wayland.")
                return None
            result = subprocess.run(
                ["wl-paste", "--type", "image/png"],
                capture_output=True,
                timeout=5,
            )
        else:
            if not shutil.which("xclip"):
                logger.debug("xclip not found; clipboard unavailable on X11.")
                return None
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
                capture_output=True,
                timeout=5,
            )
    except subprocess.TimeoutExpired:
        logger.debug("Clipboard tool timed out.")
        return None
    except Exception as exc:
        logger.debug("Clipboard read error: %s", exc)
        return None

    if result.returncode != 0 or not result.stdout:
        return None

    try:
        img = Image.open(io.BytesIO(result.stdout)).convert("RGBA")
        return img
    except Exception as exc:
        logger.debug("Could not decode clipboard image: %s", exc)
        return None
