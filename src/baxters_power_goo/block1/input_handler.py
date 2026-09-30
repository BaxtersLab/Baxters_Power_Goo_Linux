#!/usr/bin/env python3
"""
BLOCK 1 — Input Handler (Linux)
Loads images from files, URLs, and the system clipboard.
Clipboard access uses clipboard_linux.py (xclip / wl-paste) instead of
PIL.ImageGrab, which is Windows-only.
"""

import io
import logging
import urllib.request
from pathlib import Path
from typing import Optional, Union

from PIL import Image

from baxters_power_goo.error_handler import InputError

logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


class InputHandler:
    """Load images from various sources and normalise them to PIL RGBA."""

    def load_from_file(self, path: Union[str, Path]) -> Image.Image:
        """
        Open *path* and return a PIL RGBA Image.

        Raises:
            InputError — if the file does not exist, is unsupported, or
                         cannot be decoded.
        """
        path = Path(path)
        if not path.is_file():
            raise InputError(f"File not found: {path}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise InputError(
                f"Unsupported format '{path.suffix}'.  "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        try:
            img = Image.open(path).convert("RGBA")
            logger.info("Loaded image from file: %s  (%dx%d)", path, *img.size)
            return img
        except Exception as exc:
            raise InputError(f"Cannot open image '{path}': {exc}") from exc

    def load_from_url(self, url: str, timeout: int = 15) -> Image.Image:
        """
        Download *url* and return a PIL RGBA Image.

        Raises:
            InputError — on network error, HTTP error, or decode failure.
        """
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "BaxtersPowerGoo/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            logger.info("Loaded image from URL: %s  (%dx%d)", url, *img.size)
            return img
        except InputError:
            raise
        except Exception as exc:
            raise InputError(f"Cannot load image from URL '{url}': {exc}") from exc

    def load_from_clipboard(self) -> Optional[Image.Image]:
        """
        Return the current clipboard image as RGBA, or *None*.

        Uses ``clipboard_linux.paste_image_from_clipboard`` which calls
        ``xclip`` (X11) or ``wl-paste`` (Wayland).
        """
        from baxters_power_goo.clipboard_linux import paste_image_from_clipboard
        img = paste_image_from_clipboard()
        if img is not None:
            logger.info("Loaded image from clipboard  (%dx%d)", *img.size)
        else:
            logger.debug("Clipboard contained no image.")
        return img

    def load(self, source: Union[str, Path]) -> Image.Image:
        """
        Auto-detect source type (URL vs file path) and load.

        Raises:
            InputError — if loading fails.
        """
        s = str(source)
        if s.startswith(("http://", "https://")):
            return self.load_from_url(s)
        return self.load_from_file(source)
