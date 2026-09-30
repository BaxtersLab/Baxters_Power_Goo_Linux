#!/usr/bin/env python3
"""
BLOCK 5 — Render Pipeline
Post-processes the deformed image: colour correction, sharpening,
compositing onto a preview background, and final export preparation.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False

from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    PNG = "png"
    JPEG = "jpeg"
    BMP = "bmp"
    TIFF = "tiff"


@dataclass
class RenderSettings:
    output_format: OutputFormat = OutputFormat.PNG
    jpeg_quality: int = 90
    sharpen_amount: float = 0.5          # 0 = none, 1 = strong
    brightness_adjust: float = 1.0       # 1.0 = unchanged
    contrast_adjust: float = 1.0
    saturation_adjust: float = 1.0
    add_goo_vignette: bool = True
    background_colour: Tuple[int, int, int, int] = (30, 30, 30, 255)
    output_size: Optional[Tuple[int, int]] = None   # None = keep original
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderResult:
    image: Image.Image
    format: OutputFormat
    settings_applied: RenderSettings
    pipeline_steps: list = field(default_factory=list)


class RenderPipeline:
    """Post-process a deformed image for final output."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("RenderPipeline")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        image: Image.Image,
        settings: Optional[RenderSettings] = None,
        asset_package: Any = None,
    ) -> RenderResult:
        """
        Apply all post-processing steps and return a RenderResult.

        *image*          — PIL RGBA Image (output from DeformationEngine).
        *settings*       — RenderSettings; if None, defaults are used.
        *asset_package*  — optional; used to honour the performance profile.
        """
        if settings is None:
            settings = RenderSettings()

        self.logger.info("🖌️  Rendering (%dx%d)…", *image.size)
        steps: list = []

        img = image.convert("RGBA")

        # 1. Resize if requested
        if settings.output_size and settings.output_size != img.size:
            img = img.resize(settings.output_size, Image.LANCZOS)
            steps.append("resize")

        # 2. Colour adjustments
        img = self._apply_colour_adjustments(img, settings)
        steps.append("colour_adjust")

        # 3. Sharpening
        if settings.sharpen_amount > 0.0:
            img = self._apply_sharpening(img, settings.sharpen_amount)
            steps.append("sharpen")

        # 4. Goo vignette
        if settings.add_goo_vignette:
            img = self._apply_vignette(img)
            steps.append("vignette")

        # 5. Composite onto background
        img = self._composite_on_background(img, settings.background_colour)
        steps.append("composite")

        # 6. Convert to target format's colour mode
        if settings.output_format == OutputFormat.JPEG:
            img = img.convert("RGB")
        steps.append(f"convert_to_{settings.output_format.value}")

        self.logger.info("✅ Render complete — steps: %s", steps)
        return RenderResult(
            image=img,
            format=settings.output_format,
            settings_applied=settings,
            pipeline_steps=steps,
        )

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    def _apply_colour_adjustments(
        self, img: Image.Image, settings: RenderSettings
    ) -> Image.Image:
        if settings.brightness_adjust != 1.0:
            img = ImageEnhance.Brightness(img).enhance(settings.brightness_adjust)
        if settings.contrast_adjust != 1.0:
            img = ImageEnhance.Contrast(img).enhance(settings.contrast_adjust)
        if settings.saturation_adjust != 1.0:
            img = ImageEnhance.Color(img).enhance(settings.saturation_adjust)
        return img

    def _apply_sharpening(self, img: Image.Image, amount: float) -> Image.Image:
        # amount 0-1 → enhancer factor 1.0-2.0
        factor = 1.0 + amount
        return ImageEnhance.Sharpness(img).enhance(factor)

    def _apply_vignette(self, img: Image.Image) -> Image.Image:
        """Blend a dark radial vignette onto the image alpha."""
        if not _NUMPY:
            return img  # Skip vignette if numpy not available
        w, h = img.size
        y, x = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        dist = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2)
        vignette = np.clip(1.0 - dist * 0.55, 0.3, 1.0)

        arr = np.asarray(img).copy().astype(np.float32)
        for c in range(3):
            arr[:, :, c] *= vignette

        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    def _composite_on_background(
        self, img: Image.Image, bg_colour: Tuple[int, int, int, int]
    ) -> Image.Image:
        bg = Image.new("RGBA", img.size, bg_colour)
        bg.paste(img, mask=img.split()[3])
        return bg
