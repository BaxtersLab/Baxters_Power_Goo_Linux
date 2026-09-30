"""
tests/test_bpg_full.py
Full-pipeline integration tests for Baxters Power Goo.
Runs without PyQt6 (no QApplication required).
Requires: numpy, Pillow, scipy (or runs partial tests if scipy absent).
"""

import sys
import os
import pytest
from pathlib import Path
from PIL import Image
import numpy as np

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ---------------------------------------------------------------------------
# Block 2 — PowerGooBrain
# ---------------------------------------------------------------------------

class TestPowerGooBrain:
    def _brain(self):
        from baxters_power_goo.block2.power_goo_brain import PowerGooBrain
        return PowerGooBrain()

    def _small_image(self) -> Image.Image:
        arr = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        return Image.fromarray(arr, "RGB")

    def test_analyse_returns_plan(self):
        brain = self._brain()
        plan = brain.analyse(self._small_image())
        assert plan is not None

    def test_plan_has_required_fields(self):
        from baxters_power_goo.block2.power_goo_brain import GooGenPlan
        brain = self._brain()
        plan = brain.analyse(self._small_image())
        assert isinstance(plan, GooGenPlan)
        assert plan.pipeline_type is not None
        assert plan.performance_profile is not None
        assert len(plan.shader_stack) >= 1
        assert len(plan.brush_set) >= 1

    def test_foley_map_matches_brushes(self):
        brain = self._brain()
        plan = brain.analyse(self._small_image())
        assert len(plan.foley_map) == len(plan.brush_set)

    def test_large_image_uses_standard_pipeline(self):
        from baxters_power_goo.block2.power_goo_brain import PipelineType
        brain = self._brain()
        big = Image.fromarray(
            np.zeros((1000, 2000, 3), dtype=np.uint8), "RGB"
        )
        plan = brain.analyse(big)
        assert plan.pipeline_type in (PipelineType.STANDARD, PipelineType.HIGH)

    def test_tiny_image_uses_mobile_pipeline(self):
        from baxters_power_goo.block2.power_goo_brain import PipelineType
        brain = self._brain()
        tiny = Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8), "RGB")
        plan = brain.analyse(tiny)
        assert plan.pipeline_type == PipelineType.MOBILE_OPTIMIZED


# ---------------------------------------------------------------------------
# Block 3 — AssetGenerator
# ---------------------------------------------------------------------------

class TestAssetGenerator:
    def _plan(self):
        from baxters_power_goo.block2.power_goo_brain import PowerGooBrain
        arr = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
        return PowerGooBrain().analyse(Image.fromarray(arr, "RGB"))

    def test_generate_asset_package(self):
        from baxters_power_goo.block3.asset_generation import AssetGenerator, GooAssetPackage
        pkg = AssetGenerator().generate_asset_package(self._plan())
        assert isinstance(pkg, GooAssetPackage)

    def test_brush_masks_generated(self):
        from baxters_power_goo.block3.asset_generation import AssetGenerator
        pkg = AssetGenerator().generate_asset_package(self._plan())
        assert len(pkg.brush_masks) > 0

    def test_shader_resources_generated(self):
        from baxters_power_goo.block3.asset_generation import AssetGenerator
        pkg = AssetGenerator().generate_asset_package(self._plan())
        assert len(pkg.shader_resources) > 0

    def test_foley_triggers_present(self):
        from baxters_power_goo.block3.asset_generation import AssetGenerator
        pkg = AssetGenerator().generate_asset_package(self._plan())
        assert len(pkg.foley_triggers) > 0

    def test_brush_mask_data_is_float_array(self):
        from baxters_power_goo.block3.asset_generation import AssetGenerator
        pkg = AssetGenerator().generate_asset_package(self._plan())
        for bm in pkg.brush_masks:
            assert isinstance(bm.data, np.ndarray)
            assert bm.data.dtype in (np.float32, np.float64)


# ---------------------------------------------------------------------------
# Block 4 — DeformationEngine
# ---------------------------------------------------------------------------

class TestDeformationEngine:
    def _image(self) -> Image.Image:
        arr = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
        return Image.fromarray(arr, "RGB")

    def _package(self):
        from baxters_power_goo.block2.power_goo_brain import PowerGooBrain
        from baxters_power_goo.block3.asset_generation import AssetGenerator
        plan = PowerGooBrain().analyse(self._image())
        return AssetGenerator().generate_asset_package(plan)

    def test_deform_returns_pil_image(self):
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        result = DeformationEngine().deform(self._image(), self._package())
        assert isinstance(result.image, Image.Image)

    def test_output_size_matches_input(self):
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        src = self._image()
        result = DeformationEngine().deform(src, self._package())
        assert result.image.size == src.size

    def test_result_is_rgba(self):
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        result = DeformationEngine().deform(self._image(), self._package())
        assert result.image.mode == "RGBA"


# ---------------------------------------------------------------------------
# Block 5 — RenderPipeline
# ---------------------------------------------------------------------------

class TestRenderPipeline:
    def _rgba_image(self) -> Image.Image:
        arr = np.random.randint(0, 255, (128, 128, 4), dtype=np.uint8)
        return Image.fromarray(arr, "RGBA")

    def test_render_default_settings(self):
        from baxters_power_goo.block5.render_pipeline import RenderPipeline, RenderResult
        result = RenderPipeline().render(self._rgba_image())
        assert isinstance(result, RenderResult)
        assert result.image is not None

    def test_render_returns_pil(self):
        from baxters_power_goo.block5.render_pipeline import RenderPipeline
        result = RenderPipeline().render(self._rgba_image())
        assert isinstance(result.image, Image.Image)

    def test_render_steps_logged(self):
        from baxters_power_goo.block5.render_pipeline import RenderPipeline
        result = RenderPipeline().render(self._rgba_image())
        assert len(result.pipeline_steps) >= 3

    def test_jpeg_output_is_rgb(self):
        from baxters_power_goo.block5.render_pipeline import RenderPipeline, RenderSettings, OutputFormat
        settings = RenderSettings(output_format=OutputFormat.JPEG)
        result = RenderPipeline().render(self._rgba_image(), settings=settings)
        assert result.image.mode == "RGB"


# ---------------------------------------------------------------------------
# Block 1 — InputHandler
# ---------------------------------------------------------------------------

class TestInputHandler:
    def test_load_from_file(self, tmp_path):
        from baxters_power_goo.block1.input_handler import InputHandler
        img = Image.new("RGB", (32, 32), color=(100, 150, 200))
        p = tmp_path / "test.png"
        img.save(p)
        loaded = InputHandler().load_from_file(p)
        assert loaded.size == (32, 32)
        assert loaded.mode == "RGBA"

    def test_load_missing_file_raises(self):
        from baxters_power_goo.block1.input_handler import InputHandler, InputError
        with pytest.raises(InputError):
            InputHandler().load_from_file("/nonexistent/path.png")

    def test_load_unsupported_extension_raises(self, tmp_path):
        from baxters_power_goo.block1.input_handler import InputHandler, InputError
        p = tmp_path / "test.xyz"
        p.write_bytes(b"fake")
        with pytest.raises(InputError):
            InputHandler().load_from_file(p)

    def test_load_clipboard_returns_none_when_unavailable(self, monkeypatch):
        from baxters_power_goo.block1.input_handler import InputHandler
        import baxters_power_goo.clipboard_linux as cl
        monkeypatch.setattr(cl, "paste_image_from_clipboard", lambda: None)
        result = InputHandler().load_from_clipboard()
        assert result is None


# ---------------------------------------------------------------------------
# Full pipeline smoke test
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_end_to_end(self, tmp_path):
        """Load → Brain → Assets → Deform → Render → Save."""
        from baxters_power_goo.block1.input_handler import InputHandler
        from baxters_power_goo.block2.power_goo_brain import PowerGooBrain
        from baxters_power_goo.block3.asset_generation import AssetGenerator
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        from baxters_power_goo.block5.render_pipeline import RenderPipeline

        # Create a test image
        arr = np.random.randint(50, 200, (150, 150, 3), dtype=np.uint8)
        img = Image.fromarray(arr, "RGB")
        src = tmp_path / "input.png"
        img.save(src)

        # Run pipeline
        loaded = InputHandler().load_from_file(src)
        plan = PowerGooBrain().analyse(loaded)
        package = AssetGenerator().generate_asset_package(plan)
        deformed = DeformationEngine().deform(loaded, package)
        rendered = RenderPipeline().render(deformed.image)

        # Save
        out = tmp_path / "output.png"
        rendered.image.save(out)

        assert out.is_file()
        result = Image.open(out)
        assert result.size == img.size


# ---------------------------------------------------------------------------
# Goo tools — Bubble / Squeeze / Smear / Sharpen
#
# The GUI used to wire a single button to one hardcoded pipeline (what these
# tests call Bubble). These tests cover the tool concept added in
# baxters_power_goo.goo_tools and the two new DeformationEngine methods it
# calls (deform_squeeze, deform_smear_only). None of this imports PyQt6 —
# goo_tools.py is pure PIL/numpy plumbing over blocks 2-5.
# ---------------------------------------------------------------------------

class TestSqueezeTool:
    """DeformationEngine.deform_squeeze — the Squeeze tool, built from
    scratch as the inward-pinch inverse of the outward warp _apply_warp_field
    produces for Bubble."""

    def _marker_image(self, size=200, offset=(7, 50), marker_size=14):
        """Flat dark background with a small bright marker off-centre."""
        arr = np.full((size, size, 3), 30, dtype=np.uint8)
        cy = cx = size // 2
        ox, oy = offset
        y0, y1 = cy + oy - marker_size // 2, cy + oy + marker_size // 2
        x0, x1 = cx + ox - marker_size // 2, cx + ox + marker_size // 2
        arr[y0:y1, x0:x1] = (255, 40, 40)
        return Image.fromarray(arr, "RGB"), (cx, cy)

    def _marker_centroid(self, img: Image.Image):
        arr = np.asarray(img.convert("RGB"), dtype=np.float32)
        mask = (arr[:, :, 0] > 150) & (arr[:, :, 1] < 100) & (arr[:, :, 2] < 100)
        ys, xs = np.nonzero(mask)
        assert len(xs) > 0, "marker not found in image"
        return float(np.mean(xs)), float(np.mean(ys))

    def test_deform_squeeze_returns_pil_image(self):
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        img, _ = self._marker_image()
        result = DeformationEngine().deform_squeeze(img)
        assert isinstance(result.image, Image.Image)

    def test_deform_squeeze_preserves_size_and_mode(self):
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        img, _ = self._marker_image()
        result = DeformationEngine().deform_squeeze(img)
        assert result.image.size == img.size
        assert result.image.mode == "RGBA"

    def test_squeeze_pulls_content_toward_centre(self):
        """The defining behaviour of a pinch/squeeze: content off-centre
        must end up measurably closer to the image centre — proving this
        is a real inward warp and not just noise."""
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        img, (cx, cy) = self._marker_image()
        before_x, before_y = self._marker_centroid(img)
        before_dist = ((before_x - cx) ** 2 + (before_y - cy) ** 2) ** 0.5

        result = DeformationEngine().deform_squeeze(img, strength=1.0)
        after_x, after_y = self._marker_centroid(result.image)
        after_dist = ((after_x - cx) ** 2 + (after_y - cy) ** 2) ** 0.5

        assert after_dist < before_dist * 0.75, (
            f"marker did not move meaningfully toward centre: "
            f"before={before_dist:.1f}px after={after_dist:.1f}px"
        )


class TestSmearTool:
    """DeformationEngine.deform_smear_only — the existing brush-deformation
    logic (_apply_brush_deformations / _apply_single_brush), exposed as a
    standalone tool instead of always folded into deform()."""

    def _checker_image(self, size=200, cell=6):
        y, x = np.mgrid[0:size, 0:size]
        pattern = (((x // cell) + (y // cell)) % 2).astype(np.uint8)
        arr = np.zeros((size, size, 3), dtype=np.uint8)
        arr[..., 0] = np.where(pattern == 1, 220, 20)
        arr[..., 1] = np.where(pattern == 1, 200, 30)
        arr[..., 2] = np.where(pattern == 1, 60, 40)
        return Image.fromarray(arr, "RGB")

    def _package(self, img):
        from baxters_power_goo.block2.power_goo_brain import PowerGooBrain
        from baxters_power_goo.block3.asset_generation import AssetGenerator
        plan = PowerGooBrain().analyse(img)
        return AssetGenerator().generate_asset_package(plan)

    def test_deform_smear_only_returns_pil_image(self):
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        img = self._checker_image()
        result = DeformationEngine().deform_smear_only(img, self._package(img))
        assert isinstance(result.image, Image.Image)
        assert result.image.size == img.size

    def test_smear_changes_only_the_brush_patch_region(self):
        """Smear is a local brush effect — corners far from the centred
        brush patch must be untouched, while the centre (where
        _apply_single_brush always places its patch) must visibly change."""
        from baxters_power_goo.block4.deformation_engine import DeformationEngine
        img = self._checker_image()
        result = DeformationEngine().deform_smear_only(img, self._package(img))

        src_arr = np.asarray(img.convert("RGBA"))
        out_arr = np.asarray(result.image)

        assert np.array_equal(src_arr[:5, :5], out_arr[:5, :5]), \
            "far corner should be untouched by a local smear"
        assert np.array_equal(src_arr[-5:, -5:], out_arr[-5:, -5:]), \
            "far corner should be untouched by a local smear"

        diff = np.abs(src_arr.astype(int) - out_arr.astype(int)).sum(axis=2)
        assert (diff > 3).sum() > 50, "smear should visibly change pixels near the image centre"


class TestSharpenTool:
    """RenderPipeline's sharpening step, exposed as a standalone Sharpen
    tool instead of an always-on step forced into every render()."""

    def _marker_image(self, size=200):
        arr = np.full((size, size, 3), 30, dtype=np.uint8)
        arr[93:107, 93:107] = (255, 40, 40)
        return Image.fromarray(arr, "RGB")

    def test_sharpen_tool_leaves_flat_regions_untouched(self):
        """Sharpening only affects local contrast at edges. A flat region
        far from any edge should come back byte-identical — including no
        vignette darkening, proving Sharpen is no longer forced through
        the always-on vignette/composite steps alongside sharpening."""
        from baxters_power_goo.goo_tools import GooTool, run_goo_tool
        img = self._marker_image()
        result = run_goo_tool(img, GooTool.SHARPEN)

        src_rgb = np.asarray(img.convert("RGB"))
        out_rgb = np.asarray(result.convert("RGB"))

        assert np.array_equal(src_rgb[:5, :5], out_rgb[:5, :5]), \
            "flat corner should be unchanged by sharpening alone"
        assert not np.array_equal(src_rgb, out_rgb), \
            "sharpen should visibly change the image somewhere (near the edge)"


class TestGooToolsAreDistinct:
    """The core regression: all four tools must be genuinely different
    operations, not the same pipeline wearing four different labels."""

    def _checker_image(self, size=200, cell=6):
        y, x = np.mgrid[0:size, 0:size]
        pattern = (((x // cell) + (y // cell)) % 2).astype(np.uint8)
        arr = np.zeros((size, size, 3), dtype=np.uint8)
        arr[..., 0] = np.where(pattern == 1, 220, 20)
        arr[..., 1] = np.where(pattern == 1, 200, 30)
        arr[..., 2] = np.where(pattern == 1, 60, 40)
        return Image.fromarray(arr, "RGB")

    def test_exactly_four_tools_named_correctly(self):
        from baxters_power_goo.goo_tools import GooTool
        names = {t.name for t in GooTool}
        assert names == {"BUBBLE", "SQUEEZE", "SMEAR", "SHARPEN"}

    def test_squeeze_output_differs_from_bubble_output(self):
        """The specific regression the assignment calls out by name:
        Squeeze must not secretly be Bubble under a different label."""
        from baxters_power_goo.goo_tools import GooTool, run_goo_tool
        img = self._checker_image()

        bubble = np.asarray(run_goo_tool(img, GooTool.BUBBLE).convert("RGB"))
        squeeze = np.asarray(run_goo_tool(img, GooTool.SQUEEZE).convert("RGB"))

        assert bubble.shape == squeeze.shape
        assert not np.array_equal(bubble, squeeze)
        mean_abs_diff = np.abs(bubble.astype(int) - squeeze.astype(int)).mean()
        assert mean_abs_diff > 5.0, (
            f"Bubble and Squeeze outputs are suspiciously similar "
            f"(mean abs diff={mean_abs_diff:.3f}) — they may be the same code path"
        )

    def test_all_four_tools_pairwise_distinct(self):
        from baxters_power_goo.goo_tools import GooTool, run_goo_tool
        img = self._checker_image()

        outputs = {tool: np.asarray(run_goo_tool(img, tool).convert("RGB")) for tool in GooTool}
        tools = list(outputs)
        for i in range(len(tools)):
            for j in range(i + 1, len(tools)):
                a, b = outputs[tools[i]], outputs[tools[j]]
                assert a.shape == b.shape
                assert not np.array_equal(a, b), \
                    f"{tools[i].value} and {tools[j].value} produced identical output"

    def test_all_four_tools_change_the_source_image(self):
        from baxters_power_goo.goo_tools import GooTool, run_goo_tool
        img = self._checker_image()
        src = np.asarray(img.convert("RGB"))
        for tool in GooTool:
            out = np.asarray(run_goo_tool(img, tool).convert("RGB"))
            assert not np.array_equal(src, out), f"{tool.value} did not change the image at all"
