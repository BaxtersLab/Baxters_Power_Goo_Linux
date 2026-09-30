#!/usr/bin/env python3
"""
BLOCK 2 — Power Goo Brain
Analyses an input image and produces a *GooGenPlan* — the structured
blueprint consumed by Block 3 (AssetGenerator) and beyond.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerated types
# ---------------------------------------------------------------------------

class PipelineType(Enum):
    STANDARD = "standard"
    MOBILE_OPTIMIZED = "mobile_optimized"
    CPU_SAFE = "cpu_safe"
    HIGH = "high"


class PerformanceProfile(Enum):
    STANDARD = "standard"
    MOBILE_OPTIMIZED = "mobile_optimized"
    CPU_SAFE = "cpu_safe"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Plan component dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ShaderConfig:
    name: str
    type: str           # "displacement" | "flow"
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrushConfig:
    name: str
    behavior: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FoleyMapping:
    brush_type: str
    sound_trigger: str


@dataclass
class GooGenPlan:
    """Full blueprint for the goo-generation pipeline."""
    pipeline_type: PipelineType
    shader_stack: List[ShaderConfig]
    brush_set: List[BrushConfig]
    warp_fields: Optional[List[str]]
    foley_map: List[FoleyMapping]
    animation_profile: Optional[Dict[str, Any]]
    performance_profile: PerformanceProfile
    source_image: Any           # PIL Image kept for downstream use
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Brain
# ---------------------------------------------------------------------------

class PowerGooBrain:
    """
    Analyses an input image and returns a GooGenPlan tailored to
    the image's characteristics (size, complexity, colour palette).
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("PowerGooBrain")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(self, image: Image.Image) -> GooGenPlan:
        """
        Main entry point.  Takes a PIL Image, returns a GooGenPlan.
        """
        self.logger.info("🧠 Analysing image (%dx%d)…", *image.size)

        metrics = self._compute_metrics(image)
        pipeline_type, perf_profile = self._select_pipeline(metrics)
        shader_stack = self._build_shader_stack(metrics, pipeline_type)
        brush_set = self._build_brush_set(metrics, pipeline_type)
        warp_fields = self._select_warp_fields(metrics, pipeline_type)
        foley_map = self._build_foley_map(brush_set)
        animation_profile = self._build_animation_profile(metrics)

        plan = GooGenPlan(
            pipeline_type=pipeline_type,
            shader_stack=shader_stack,
            brush_set=brush_set,
            warp_fields=warp_fields,
            foley_map=foley_map,
            animation_profile=animation_profile,
            performance_profile=perf_profile,
            source_image=image,
            metadata=metrics,
        )

        self.logger.info(
            "✅ Plan ready: %s  |  %d shaders  |  %d brushes  |  warp: %s",
            pipeline_type.value, len(shader_stack), len(brush_set), warp_fields,
        )
        return plan

    # ------------------------------------------------------------------
    # Image metrics
    # ------------------------------------------------------------------

    def _compute_metrics(self, image: Image.Image) -> Dict[str, Any]:
        """Extract scalar metrics from the image."""
        w, h = image.size
        pixels = np.asarray(image.convert("RGBA"), dtype=np.float32)

        # Mean brightness (0-1)
        brightness = float(np.mean(pixels[:, :, :3]) / 255.0)

        # Edge density via simple horizontal gradient
        grey = np.mean(pixels[:, :, :3], axis=2)
        grad_h = np.abs(np.diff(grey, axis=1))
        grad_v = np.abs(np.diff(grey, axis=0))
        edge_density = float(
            (np.mean(grad_h) + np.mean(grad_v)) / (255.0 * 2)
        )

        # Colour saturation
        r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
        c_max = np.maximum(np.maximum(r, g), b)
        c_min = np.minimum(np.minimum(r, g), b)
        saturation = float(np.mean((c_max - c_min) / (c_max + 1e-6)))

        return {
            "width": w, "height": h,
            "megapixels": (w * h) / 1_000_000,
            "brightness": brightness,
            "edge_density": edge_density,
            "saturation": saturation,
        }

    # ------------------------------------------------------------------
    # Plan assembly helpers
    # ------------------------------------------------------------------

    def _select_pipeline(
        self, metrics: Dict[str, Any]
    ) -> tuple[PipelineType, PerformanceProfile]:
        mp = metrics["megapixels"]
        if mp < 0.5:
            return PipelineType.MOBILE_OPTIMIZED, PerformanceProfile.MOBILE_OPTIMIZED
        if mp < 2.0:
            return PipelineType.CPU_SAFE, PerformanceProfile.CPU_SAFE
        if mp < 8.0:
            return PipelineType.STANDARD, PerformanceProfile.STANDARD
        return PipelineType.HIGH, PerformanceProfile.HIGH

    def _build_shader_stack(
        self, metrics: Dict[str, Any], pipeline_type: PipelineType
    ) -> List[ShaderConfig]:
        shaders: List[ShaderConfig] = []

        intensity = min(1.0, 0.4 + metrics["edge_density"] * 2.0)

        shaders.append(ShaderConfig(
            name="primary_displacement",
            type="displacement",
            parameters={"intensity": intensity, "mode": "radial"},
        ))

        if pipeline_type in (PipelineType.STANDARD, PipelineType.HIGH):
            shaders.append(ShaderConfig(
                name="flow_overlay",
                type="flow",
                parameters={
                    "viscosity": 0.5 + metrics["saturation"] * 0.3,
                    "flow_rate": 0.4 + metrics["brightness"] * 0.2,
                },
            ))

        if pipeline_type == PipelineType.HIGH:
            shaders.append(ShaderConfig(
                name="chaos_blend",
                type="displacement",
                parameters={"intensity": 0.6, "mode": "vortex"},
            ))

        return shaders

    def _build_brush_set(
        self, metrics: Dict[str, Any], pipeline_type: PipelineType
    ) -> List[BrushConfig]:
        softness = max(0.1, 1.0 - metrics["edge_density"] * 2)

        brushes = [
            BrushConfig(name="standard_brush",   behavior={"softness": softness, "size": 64}),
            BrushConfig(name="smear_brush",      behavior={"softness": softness * 0.7, "size": 48, "flow": 0.8}),
            BrushConfig(name="turbulence_brush", behavior={"softness": softness * 0.5, "size": 80, "chaos": 0.6}),
        ]

        if pipeline_type in (PipelineType.STANDARD, PipelineType.HIGH):
            brushes.append(
                BrushConfig(name="pull_brush", behavior={"softness": 0.6, "size": 96, "pull": True})
            )

        return brushes

    def _select_warp_fields(
        self, metrics: Dict[str, Any], pipeline_type: PipelineType
    ) -> Optional[List[str]]:
        if pipeline_type == PipelineType.MOBILE_OPTIMIZED:
            return None
        fields = ["flow_lines"]
        if metrics["edge_density"] > 0.1:
            fields.append("vortex_field")
        if pipeline_type in (PipelineType.STANDARD, PipelineType.HIGH):
            fields.append("turbulence_field")
        if pipeline_type == PipelineType.HIGH:
            fields.append("chaos_mesh")
        return fields

    def _build_foley_map(self, brush_set: List[BrushConfig]) -> List[FoleyMapping]:
        sound_table = {
            "standard_brush":   "spring_twang",
            "smear_brush":      "slow_slurp",
            "turbulence_brush": "coil_bounce",
            "pull_brush":       "bubble_pop",
        }
        return [
            FoleyMapping(brush_type=b.name, sound_trigger=sound_table.get(b.name, "spring_twang"))
            for b in brush_set
        ]

    def _build_animation_profile(
        self, metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        # Animation is opt-in; only enable for small images to avoid memory issues
        if metrics["megapixels"] < 1.0:
            return {"frame_rate": 24, "duration": 3.0}
        return None
