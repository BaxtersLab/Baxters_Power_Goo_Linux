#!/usr/bin/env python3
"""
Goo Tools — the four user-selectable Power Goo tools.

Bubble, Squeeze, Smear, and Sharpen each run a genuinely distinct operation
against the block1-5 pipeline. This module only decides *which* block
methods run for a given tool; it does not change any block's own logic.

- Bubble  — the original full pipeline (Brain -> AssetGenerator ->
            DeformationEngine.deform -> RenderPipeline.render), unchanged.
- Squeeze — DeformationEngine.deform_squeeze only: a standalone inward
            pinch warp, the geometric inverse of the outward warp fields
            Bubble applies.
- Smear   — DeformationEngine.deform_smear_only: the existing brush
            deformation logic, run standalone instead of folded into the
            full deform() pipeline.
- Sharpen — RenderPipeline.render with sharpening as the only active step:
            the existing sharpen post-process, run standalone instead of
            always-on alongside vignette/composite on every render.
"""

from enum import Enum

from PIL import Image

from baxters_power_goo.block2.power_goo_brain import PowerGooBrain
from baxters_power_goo.block3.asset_generation import AssetGenerator
from baxters_power_goo.block4.deformation_engine import DeformationEngine
from baxters_power_goo.block5.render_pipeline import RenderPipeline, RenderSettings


class GooTool(Enum):
    BUBBLE = "bubble"
    SQUEEZE = "squeeze"
    SMEAR = "smear"
    SHARPEN = "sharpen"


TOOL_LABELS = {
    GooTool.BUBBLE: "🫧 Bubble",
    GooTool.SQUEEZE: "🤏 Squeeze",
    GooTool.SMEAR: "👉 Smear",
    GooTool.SHARPEN: "🔪 Sharpen",
}


def run_goo_tool(image: Image.Image, tool: GooTool) -> Image.Image:
    """Run *tool* against *image* and return the resulting PIL Image."""
    if tool == GooTool.BUBBLE:
        return _run_bubble(image)
    if tool == GooTool.SQUEEZE:
        return _run_squeeze(image)
    if tool == GooTool.SMEAR:
        return _run_smear(image)
    if tool == GooTool.SHARPEN:
        return _run_sharpen(image)
    raise ValueError(f"Unknown Goo tool: {tool!r}")


def _run_bubble(image: Image.Image) -> Image.Image:
    """Bubble — the original, unmodified full pipeline."""
    brain = PowerGooBrain()
    plan = brain.analyse(image)

    generator = AssetGenerator()
    asset_package = generator.generate_asset_package(plan)

    engine = DeformationEngine()
    deform_result = engine.deform(image, asset_package)

    pipeline = RenderPipeline()
    render_result = pipeline.render(deform_result.image)
    return render_result.image


def _run_squeeze(image: Image.Image) -> Image.Image:
    """Squeeze — standalone inward pinch warp."""
    engine = DeformationEngine()
    deform_result = engine.deform_squeeze(image)
    return deform_result.image


def _run_smear(image: Image.Image) -> Image.Image:
    """Smear — the existing brush-deformation logic, standalone."""
    brain = PowerGooBrain()
    plan = brain.analyse(image)

    generator = AssetGenerator()
    asset_package = generator.generate_asset_package(plan)

    engine = DeformationEngine()
    deform_result = engine.deform_smear_only(image, asset_package)
    return deform_result.image


def _run_sharpen(image: Image.Image) -> Image.Image:
    """Sharpen — the existing sharpen post-process, standalone."""
    pipeline = RenderPipeline()
    settings = RenderSettings(
        sharpen_amount=1.0,
        add_goo_vignette=False,
        brightness_adjust=1.0,
        contrast_adjust=1.0,
        saturation_adjust=1.0,
    )
    render_result = pipeline.render(image, settings=settings)
    return render_result.image
