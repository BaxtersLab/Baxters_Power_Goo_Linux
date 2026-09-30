#!/usr/bin/env python3
"""
BLOCK 4 — Deformation Engine
Applies goo-style warp deformations to a PIL image using the
GooAssetPackage produced by Block 3.  SciPy is used when available
for high-quality warping; a pure-NumPy fallback handles the CPU-safe
and mobile-optimised profiles.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from scipy.ndimage import map_coordinates, gaussian_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class DeformationResult:
    image: Image.Image
    warp_maps_applied: List[str] = field(default_factory=list)
    brush_masks_used: int = 0
    performance_profile: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DeformationEngine:
    """Apply goo deformations to an image from a GooAssetPackage."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("DeformationEngine")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deform(self, source: Image.Image, asset_package: Any) -> DeformationResult:
        """
        Apply all deformations described in *asset_package* to *source*.

        Returns a DeformationResult containing the warped image.
        """
        self.logger.info("🌊 Starting deformation (%dx%d)…", *source.size)

        img_array = np.asarray(source.convert("RGBA"), dtype=np.float32) / 255.0
        profile = asset_package.performance_profile
        applied: List[str] = []

        # Apply warp fields
        for warp_field in asset_package.warp_fields:
            img_array = self._apply_warp_field(img_array, warp_field, profile)
            applied.append(warp_field.name)

        # Apply brush-based deformations
        brushes_used = 0
        if asset_package.brush_masks:
            img_array, brushes_used = self._apply_brush_deformations(
                img_array, asset_package.brush_masks, profile
            )

        # Apply displacement maps
        for dmap in asset_package.displacement_maps:
            img_array = self._apply_displacement_map(img_array, dmap)

        # Clamp and convert back to PIL
        img_array = np.clip(img_array * 255.0, 0, 255).astype(np.uint8)
        result_image = Image.fromarray(img_array, "RGBA")

        self.logger.info(
            "✅ Deformation done — %d warp fields, %d brushes",
            len(applied), brushes_used,
        )
        return DeformationResult(
            image=result_image,
            warp_maps_applied=applied,
            brush_masks_used=brushes_used,
            performance_profile=profile,
            metadata={"warp_fields": applied},
        )

    # ------------------------------------------------------------------
    # Squeeze tool — standalone inward pinch warp
    # ------------------------------------------------------------------

    def deform_squeeze(
        self, source: Image.Image, strength: float = 1.0
    ) -> DeformationResult:
        """
        Apply an inward pinch warp — the Squeeze tool.

        This is the geometric inverse of the outward "bubble" warp that
        ``_apply_warp_field`` produces: a bulge samples each destination
        pixel from a source point *closer* to the centre than itself
        (stretching centre content outward). Squeeze inverts that —  it
        samples from a source point *farther* from the centre than the
        destination, which pulls surrounding content in toward the middle.
        Content at the exact centre and at/beyond the pinch radius is left
        in place, so the warp is concentrated in a circular region around
        the image centre.
        """
        self.logger.info("🤏 Starting squeeze deformation (%dx%d)…", *source.size)

        img_array = np.asarray(source.convert("RGBA"), dtype=np.float32) / 255.0
        h, w = img_array.shape[:2]

        cy, cx = h / 2.0, w / 2.0
        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
        dy = y_coords - cy
        dx = x_coords - cx
        dist = np.sqrt(dx ** 2 + dy ** 2)

        # Pinch reaches out to the nearer edge of the image; beyond that
        # radius the image is left untouched.
        radius = max(1.0, min(cx, cy))
        norm_r = np.clip(dist / radius, 0.0, 1.0)

        # A bulge would sample source radius = dest_radius ** (1 + strength)
        # (exponent > 1, pulls from *closer* to centre). Squeeze inverts
        # the exponent to < 1, sampling from *farther* out instead.
        exponent = 1.0 / (1.0 + strength)
        src_dist = np.where(dist <= radius, (norm_r ** exponent) * radius, dist)

        angle = np.arctan2(dy, dx)
        src_x = np.clip(cx + src_dist * np.cos(angle), 0, w - 1)
        src_y = np.clip(cy + src_dist * np.sin(angle), 0, h - 1)

        img_array = self._remap(img_array, src_x, src_y, "standard")
        img_array = np.clip(img_array * 255.0, 0, 255).astype(np.uint8)
        result_image = Image.fromarray(img_array, "RGBA")

        self.logger.info("✅ Squeeze deformation done")
        return DeformationResult(
            image=result_image,
            warp_maps_applied=["squeeze_pinch"],
            brush_masks_used=0,
            performance_profile="standard",
            metadata={"tool": "squeeze", "strength": strength},
        )

    # ------------------------------------------------------------------
    # Smear tool — standalone brush deformation
    # ------------------------------------------------------------------

    def deform_smear_only(
        self, source: Image.Image, asset_package: Any
    ) -> DeformationResult:
        """
        Apply only the brush-based smear deformations from *asset_package* —
        the Smear tool, run standalone instead of folded into ``deform()``
        alongside warp fields and displacement maps. Reuses
        ``_apply_brush_deformations`` unchanged.
        """
        self.logger.info("👉 Starting smear-only deformation (%dx%d)…", *source.size)

        img_array = np.asarray(source.convert("RGBA"), dtype=np.float32) / 255.0
        profile = asset_package.performance_profile

        brushes_used = 0
        if asset_package.brush_masks:
            img_array, brushes_used = self._apply_brush_deformations(
                img_array, asset_package.brush_masks, profile
            )

        img_array = np.clip(img_array * 255.0, 0, 255).astype(np.uint8)
        result_image = Image.fromarray(img_array, "RGBA")

        self.logger.info("✅ Smear-only deformation done — %d brushes", brushes_used)
        return DeformationResult(
            image=result_image,
            warp_maps_applied=[],
            brush_masks_used=brushes_used,
            performance_profile=profile,
            metadata={"tool": "smear"},
        )

    # ------------------------------------------------------------------
    # Warp field application
    # ------------------------------------------------------------------

    def _apply_warp_field(
        self, img: np.ndarray, warp_field: Any, profile: str
    ) -> np.ndarray:
        """Remap *img* according to *warp_field.displacement_map*."""
        if warp_field.displacement_map is None or warp_field.displacement_map.size == 0:
            return img

        h, w = img.shape[:2]
        disp = warp_field.displacement_map

        # Resize displacement to match image
        if disp.shape[:2] != (h, w):
            disp_img = Image.fromarray(
                np.clip((disp + 1.0) * 127.5, 0, 255).astype(np.uint8)
                if disp.ndim == 2 else
                np.clip(disp[:, :, :3] * 255, 0, 255).astype(np.uint8)
            )
            disp_img = disp_img.resize((w, h), Image.BILINEAR)
            disp = np.asarray(disp_img, dtype=np.float32) / 255.0 * 2.0 - 1.0

        # Scale displacement by ~5% of image dimensions
        scale_x = w * 0.05
        scale_y = h * 0.05

        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)

        if disp.ndim == 3 and disp.shape[2] >= 2:
            dx = disp[:, :, 0] * scale_x
            dy = disp[:, :, 1] * scale_y
        else:
            d = disp if disp.ndim == 2 else disp[:, :, 0]
            dx, dy = d * scale_x, d * scale_y

        src_x = np.clip(x_coords + dx, 0, w - 1)
        src_y = np.clip(y_coords + dy, 0, h - 1)

        return self._remap(img, src_x, src_y, profile)

    # ------------------------------------------------------------------
    # Brush deformations
    # ------------------------------------------------------------------

    def _apply_brush_deformations(
        self,
        img: np.ndarray,
        brush_masks: List[Any],
        profile: str,
    ) -> Tuple[np.ndarray, int]:
        """Apply a representative set of brush masks as smear operations."""
        h, w = img.shape[:2]
        count = 0

        # For bulk application use a subset to stay within budget
        max_brushes = 6 if profile in ("standard", "high") else 3
        for brush in brush_masks[:max_brushes]:
            img = self._apply_single_brush(img, brush, h, w)
            count += 1

        return img, count

    def _apply_single_brush(
        self, img: np.ndarray, brush: Any, h: int, w: int
    ) -> np.ndarray:
        """Blend a brush mask into the image as a local smear."""
        mask = brush.data
        if mask is None or mask.size == 0:
            return img

        # Resize mask to a patch centred in the image
        bh, bw = mask.shape[:2]
        scale = min(h // 4, w // 4, 128) / max(bh, bw, 1)
        new_bh = max(1, int(bh * scale))
        new_bw = max(1, int(bw * scale))

        mask_img = Image.fromarray(
            np.clip(mask * 255, 0, 255).astype(np.uint8)
        ).resize((new_bw, new_bh), Image.BILINEAR)
        mask_arr = np.asarray(mask_img, dtype=np.float32) / 255.0

        cy, cx = h // 2, w // 2
        y0 = max(0, cy - new_bh // 2)
        x0 = max(0, cx - new_bw // 2)
        y1 = min(h, y0 + new_bh)
        x1 = min(w, x0 + new_bw)

        patch_h, patch_w = y1 - y0, x1 - x0
        if patch_h <= 0 or patch_w <= 0:
            return img

        m = mask_arr[:patch_h, :patch_w, np.newaxis] * 0.15  # max 15% strength
        patch = img[y0:y1, x0:x1]

        # Shift patch slightly to create a smear effect
        shift = max(1, int(min(patch_h, patch_w) * 0.05))
        shifted = np.roll(patch, shift, axis=1)

        img = img.copy()
        img[y0:y1, x0:x1] = patch * (1.0 - m) + shifted * m
        return img

    # ------------------------------------------------------------------
    # Displacement map application
    # ------------------------------------------------------------------

    def _apply_displacement_map(self, img: np.ndarray, dmap: np.ndarray) -> np.ndarray:
        """Apply an RGB displacement map (values in 0-1 range)."""
        if dmap is None or dmap.size == 0:
            return img

        h, w = img.shape[:2]
        if dmap.shape[:2] != (h, w):
            dmap_img = Image.fromarray(
                np.clip(dmap * 255, 0, 255).astype(np.uint8)
            ).resize((w, h), Image.BILINEAR)
            dmap = np.asarray(dmap_img, dtype=np.float32) / 255.0

        scale = min(w, h) * 0.03
        y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)

        dx = (dmap[:, :, 0] - 0.5) * 2.0 * scale if dmap.shape[2] > 0 else np.zeros((h, w))
        dy = (dmap[:, :, 1] - 0.5) * 2.0 * scale if dmap.shape[2] > 1 else np.zeros((h, w))

        src_x = np.clip(x_coords + dx, 0, w - 1)
        src_y = np.clip(y_coords + dy, 0, h - 1)

        return self._remap(img, src_x, src_y, "standard")

    # ------------------------------------------------------------------
    # Pixel remapping helpers
    # ------------------------------------------------------------------

    def _remap(
        self,
        img: np.ndarray,
        src_x: np.ndarray,
        src_y: np.ndarray,
        profile: str,
    ) -> np.ndarray:
        """Remap *img* using float coordinate arrays."""
        if SCIPY_AVAILABLE and profile not in ("mobile_optimized",):
            channels = []
            for c in range(img.shape[2]):
                coords = [src_y, src_x]
                ch = map_coordinates(img[:, :, c], coords, order=1, mode="reflect")
                channels.append(ch)
            return np.stack(channels, axis=-1)

        # Pure-NumPy nearest-neighbour fallback
        yi = np.clip(np.round(src_y).astype(np.int32), 0, img.shape[0] - 1)
        xi = np.clip(np.round(src_x).astype(np.int32), 0, img.shape[1] - 1)
        return img[yi, xi]
