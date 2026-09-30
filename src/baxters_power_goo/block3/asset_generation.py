#!/usr/bin/env python3
"""
SUPER_BLOCK_3: Asset Generation & Deformation Resource Fabrication
Baxters Power Goo - Resource Fabrication Engine

This module generates all assets required by the Goo Build Plan, including
brush masks, displacement maps, warp fields, foley triggers, and optional
animation timeline resources.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import random
import json
from PIL import Image, ImageDraw, ImageFilter
import io

# Action sound system
from baxters_power_goo.sound_manager import SoundManager

# Optional imports for enhanced functionality
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from scipy import ndimage
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@dataclass
class BrushMask:
    """Generated brush mask for deformation"""
    name: str
    mask_type: str
    data: np.ndarray
    resolution: Tuple[int, int]
    softness: float
    directionality: Optional[str] = None


@dataclass
class WarpField:
    """Generated warp field for deformation"""
    name: str
    field_type: str
    displacement_map: np.ndarray
    flow_map: Optional[np.ndarray] = None
    region_mask: Optional[np.ndarray] = None


@dataclass
class ShaderResource:
    """Prepared shader resource"""
    name: str
    resource_type: str
    data: Any  # Could be texture, normal map, etc.
    format: str
    gpu_optimized: bool


@dataclass
class FoleyTrigger:
    """Generated foley sound trigger"""
    brush_type: str
    sound_type: str
    intensity_curve: List[float]
    pitch_range: Tuple[float, float]
    volume_range: Tuple[float, float]
    variations: List[str]


@dataclass
class AnimationResource:
    """Generated animation resource"""
    name: str
    resource_type: str
    data: Any
    keyframe_count: int
    duration: float


@dataclass
class GooAssetPackage:
    """Complete asset package for deformation pipeline"""
    brush_masks: List[BrushMask]
    warp_fields: List[WarpField]
    displacement_maps: List[np.ndarray]
    shader_resources: List[ShaderResource]
    foley_triggers: List[FoleyTrigger]
    animation_resources: List[AnimationResource]
    sound_manager: Optional[SoundManager] = None
    performance_profile: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssetGenerator:
    """Generates all assets required by the Goo Build Plan"""

    def __init__(self):
        self.logger = logging.getLogger("AssetGenerator")
        self.cache_dir = Path("cache/assets")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sound_manager = SoundManager()

    def generate_asset_package(self, goo_build_plan: Any) -> GooAssetPackage:
        """
        Generate complete asset package from goo build plan

        Args:
            goo_build_plan: Structured plan from SUPER_BLOCK_2

        Returns:
            Complete asset package ready for deformation pipeline
        """
        self.logger.info("🎨 Generating asset package from goo build plan...")

        # Extract plan components
        pipeline_type = goo_build_plan.pipeline_type
        shader_stack = goo_build_plan.shader_stack
        brush_set = goo_build_plan.brush_set
        warp_fields = goo_build_plan.warp_fields
        foley_map = goo_build_plan.foley_map
        animation_profile = goo_build_plan.animation_profile
        performance_profile = goo_build_plan.performance_profile

        # Generate all asset types
        brush_masks = self._generate_brush_masks(brush_set, performance_profile)
        warp_fields_assets = self._generate_warp_fields(warp_fields, pipeline_type, performance_profile)
        displacement_maps = self._generate_displacement_maps(warp_fields_assets, performance_profile)
        shader_resources = self._prepare_shader_resources(shader_stack, performance_profile)
        foley_triggers = self._generate_foley_triggers(foley_map, brush_set)
        animation_resources = self._generate_animation_resources(animation_profile, performance_profile)

        # Create metadata
        metadata = {
            "effect_type": pipeline_type.value,
            "brush_count": len(brush_masks),
            "warp_field_count": len(warp_fields_assets),
            "shader_count": len(shader_resources),
            "foley_trigger_count": len(foley_triggers),
            "animation_enabled": animation_profile is not None,
            "performance_optimized": performance_profile.value
        }

        # Create asset package
        asset_package = GooAssetPackage(
            brush_masks=brush_masks,
            warp_fields=warp_fields_assets,
            displacement_maps=displacement_maps,
            shader_resources=shader_resources,
            foley_triggers=foley_triggers,
            animation_resources=animation_resources,
            sound_manager=self.sound_manager,
            performance_profile=performance_profile.value,
            metadata=metadata
        )

        self.logger.info(f"✅ Asset package generated: {len(brush_masks)} brushes, {len(warp_fields_assets)} warp fields, {len(shader_resources)} shaders")
        return asset_package

    def _generate_brush_masks(self, brush_set: List[Any], performance_profile: Any) -> List[BrushMask]:
        """Generate brush masks for all brush types"""
        brush_masks = []

        # Determine resolution based on performance
        if performance_profile.value == "mobile_optimized":
            resolution = (64, 64)
        elif performance_profile.value == "cpu_safe":
            resolution = (128, 128)
        else:
            resolution = (256, 256)

        for brush_config in brush_set:
            # Generate base mask
            base_mask = self._generate_base_brush_mask(brush_config, resolution)

            # Create variants
            variants = self._create_brush_variants(base_mask, brush_config, resolution)

            brush_masks.extend(variants)

        return brush_masks

    def _generate_base_brush_mask(self, brush_config: Any, resolution: Tuple[int, int]) -> np.ndarray:
        """Generate base brush mask"""
        width, height = resolution

        # Create circular base mask
        y, x = np.ogrid[:height, :width]
        center_y, center_x = height // 2, width // 2
        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        max_distance = min(width, height) // 2

        # Create radial gradient
        mask = 1.0 - np.clip(distance / max_distance, 0, 1)

        # Apply softness
        softness = brush_config.behavior.get("softness", 0.5)
        if softness < 1.0:
            mask = np.power(mask, 1.0 / (1.0 - softness + 0.1))

        return mask

    def _create_brush_variants(self, base_mask: np.ndarray, brush_config: Any, resolution: Tuple[int, int]) -> List[BrushMask]:
        """Create soft, hard, textured, and directional variants"""
        variants = []

        # Soft variant
        soft_mask = self._apply_softness(base_mask, 0.8)
        variants.append(BrushMask(
            name=f"{brush_config.name}_soft",
            mask_type="soft",
            data=soft_mask,
            resolution=resolution,
            softness=0.8
        ))

        # Hard variant
        hard_mask = self._apply_softness(base_mask, 0.2)
        variants.append(BrushMask(
            name=f"{brush_config.name}_hard",
            mask_type="hard",
            data=hard_mask,
            resolution=resolution,
            softness=0.2
        ))

        # Textured variant
        textured_mask = self._apply_texture(base_mask)
        variants.append(BrushMask(
            name=f"{brush_config.name}_textured",
            mask_type="textured",
            data=textured_mask,
            resolution=resolution,
            softness=0.5
        ))

        # Directional variants
        for direction in ["push", "pull", "swirl"]:
            directional_mask = self._apply_directionality(base_mask, direction)
            variants.append(BrushMask(
                name=f"{brush_config.name}_{direction}",
                mask_type="directional",
                data=directional_mask,
                resolution=resolution,
                softness=0.5,
                directionality=direction
            ))

        return variants

    def _apply_softness(self, mask: np.ndarray, softness: float) -> np.ndarray:
        """Apply softness to mask"""
        if softness >= 1.0:
            return mask
        elif softness <= 0.0:
            return (mask > 0.5).astype(np.float32)

        # Apply gamma correction for softness
        return np.power(mask, 1.0 / softness)

    def _apply_texture(self, mask: np.ndarray) -> np.ndarray:
        """Apply texture to mask"""
        # Add noise for texture
        noise = np.random.normal(0, 0.1, mask.shape)
        textured = mask + noise
        return np.clip(textured, 0, 1)

    def _apply_directionality(self, mask: np.ndarray, direction: str) -> np.ndarray:
        """Apply directional bias to mask"""
        height, width = mask.shape

        if direction == "push":
            # Gradient from center outward
            y, x = np.ogrid[:height, :width]
            center_y, center_x = height // 2, width // 2
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            max_distance = min(width, height) // 2
            gradient = distance / max_distance
            return mask * (1.0 - gradient * 0.5)

        elif direction == "pull":
            # Gradient toward center
            y, x = np.ogrid[:height, :width]
            center_y, center_x = height // 2, width // 2
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            max_distance = min(width, height) // 2
            gradient = 1.0 - (distance / max_distance)
            return mask * (0.5 + gradient * 0.5)

        elif direction == "swirl":
            # Radial swirl pattern
            y, x = np.ogrid[:height, :width]
            center_y, center_x = height // 2, width // 2
            angle = np.arctan2(y - center_y, x - center_x)
            swirl = (np.sin(angle * 3) + 1) * 0.5
            return mask * (0.7 + swirl * 0.3)

        return mask

    def _generate_warp_fields(self, warp_field_names: Optional[List[str]], pipeline_type: Any, performance_profile: Any) -> List[WarpField]:
        """Generate warp fields for deformation effects"""
        warp_fields = []

        if not warp_field_names:
            return warp_fields

        # Determine resolution
        if performance_profile.value == "mobile_optimized":
            resolution = (128, 128)
        else:
            resolution = (256, 256)

        for field_name in warp_field_names:
            field = self._generate_warp_field(field_name, resolution)
            if field:
                warp_fields.append(field)

        return warp_fields

    def _generate_warp_field(self, field_name: str, resolution: Tuple[int, int]) -> Optional[WarpField]:
        """Generate a specific warp field"""
        height, width = resolution

        if field_name == "vortex_field":
            displacement = self._create_vortex_field(width, height)
            return WarpField(
                name="vortex_field",
                field_type="swirl",
                displacement_map=displacement
            )

        elif field_name == "flow_lines":
            displacement, flow = self._create_flow_field(width, height)
            return WarpField(
                name="flow_lines",
                field_type="flow",
                displacement_map=displacement,
                flow_map=flow
            )

        elif field_name == "turbulence_field":
            displacement = self._create_turbulence_field(width, height)
            return WarpField(
                name="turbulence_field",
                field_type="chaos",
                displacement_map=displacement
            )

        elif field_name == "chaos_mesh":
            displacement = self._create_chaos_mesh(width, height)
            return WarpField(
                name="chaos_mesh",
                field_type="chaotic",
                displacement_map=displacement
            )

        return None

    def _create_vortex_field(self, width: int, height: int) -> np.ndarray:
        """Create vortex displacement field"""
        y, x = np.ogrid[:height, :width]
        center_y, center_x = height // 2, width // 2

        angle = np.arctan2(y - center_y, x - center_x)
        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        max_distance = min(width, height) // 2

        strength = 1.0 - np.clip(distance / max_distance, 0, 1)
        displacement_x = np.cos(angle + distance * 0.1) * strength * 0.5
        displacement_y = np.sin(angle + distance * 0.1) * strength * 0.5

        displacement = np.stack([displacement_x, displacement_y], axis=-1)
        return displacement

    def _create_flow_field(self, width: int, height: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create flow field with displacement and flow map"""
        flow_x = self._generate_perlin_noise(width, height, scale=0.05)
        flow_y = self._generate_perlin_noise(width, height, scale=0.05, offset=1000)

        magnitude = np.sqrt(flow_x**2 + flow_y**2)
        flow_x = flow_x / (magnitude + 1e-6)
        flow_y = flow_y / (magnitude + 1e-6)

        displacement_x = flow_x * 0.3
        displacement_y = flow_y * 0.3
        displacement = np.stack([displacement_x, displacement_y], axis=-1)

        flow_map = np.stack([flow_x, flow_y], axis=-1)

        return displacement, flow_map

    def _create_turbulence_field(self, width: int, height: int) -> np.ndarray:
        """Create turbulence displacement field"""
        displacement_x = np.zeros((height, width))
        displacement_y = np.zeros((height, width))

        for octave in range(3):
            scale = 0.02 * (2 ** octave)
            amp = 0.5 ** octave

            noise_x = self._generate_perlin_noise(width, height, scale=scale, offset=octave * 1000)
            noise_y = self._generate_perlin_noise(width, height, scale=scale, offset=octave * 1000 + 500)

            displacement_x += noise_x * amp
            displacement_y += noise_y * amp

        displacement = np.stack([displacement_x, displacement_y], axis=-1)
        return displacement

    def _create_chaos_mesh(self, width: int, height: int) -> np.ndarray:
        """Create chaotic mesh displacement"""
        displacement_x = np.random.normal(0, 0.2, (height, width))
        displacement_y = np.random.normal(0, 0.2, (height, width))

        if SCIPY_AVAILABLE:
            displacement_x = ndimage.gaussian_filter(displacement_x, sigma=2)
            displacement_y = ndimage.gaussian_filter(displacement_y, sigma=2)

        displacement = np.stack([displacement_x, displacement_y], axis=-1)
        return displacement

    def _generate_perlin_noise(self, width: int, height: int, scale: float = 0.1, offset: float = 0) -> np.ndarray:
        """Generate simple Perlin-like noise"""
        y, x = np.ogrid[:height, :width]

        noise = np.sin(x * scale + offset) * np.cos(y * scale + offset)
        noise += np.sin(x * scale * 2 + offset) * 0.5 * np.cos(y * scale * 2 + offset)
        noise += np.sin(x * scale * 4 + offset) * 0.25 * np.cos(y * scale * 4 + offset)

        return noise

    def _generate_displacement_maps(self, warp_fields: List[WarpField], performance_profile: Any) -> List[np.ndarray]:
        """Generate displacement maps from warp fields"""
        displacement_maps = []

        for warp_field in warp_fields:
            displacement_map = self._warp_field_to_displacement_map(warp_field, performance_profile)
            displacement_maps.append(displacement_map)

        return displacement_maps

    def _warp_field_to_displacement_map(self, warp_field: WarpField, performance_profile: Any) -> np.ndarray:
        """Convert warp field to displacement map"""
        displacement = warp_field.displacement_map

        if displacement.size > 0:
            min_val = np.min(displacement)
            max_val = np.max(displacement)
            if max_val > min_val:
                displacement = (displacement - min_val) / (max_val - min_val)

        height, width = displacement.shape[:2]
        rgb_map = np.zeros((height, width, 3), dtype=np.float32)

        if len(displacement.shape) >= 3:
            rgb_map[:, :, 0] = (displacement[:, :, 0] + 1.0) * 0.5
            rgb_map[:, :, 1] = (displacement[:, :, 1] + 1.0) * 0.5

        magnitude = np.sqrt(displacement[:, :, 0]**2 + displacement[:, :, 1]**2)
        rgb_map[:, :, 2] = np.clip(magnitude, 0, 1)

        return rgb_map

    def _prepare_shader_resources(self, shader_stack: List[Any], performance_profile: Any) -> List[ShaderResource]:
        """Prepare shader resources for GPU"""
        shader_resources = []

        for shader_config in shader_stack:
            resource = self._create_shader_resource(shader_config, performance_profile)
            if resource:
                shader_resources.append(resource)

        return shader_resources

    def _create_shader_resource(self, shader_config: Any, performance_profile: Any) -> Optional[ShaderResource]:
        """Create a shader resource"""
        if shader_config.type == "displacement":
            resolution = (256, 256) if performance_profile.value != "mobile_optimized" else (128, 128)
            texture = self._create_displacement_texture(resolution, shader_config.parameters)

            return ShaderResource(
                name=shader_config.name,
                resource_type="displacement_texture",
                data=texture,
                format="RGB",
                gpu_optimized=True
            )

        elif shader_config.type == "flow":
            resolution = (256, 256) if performance_profile.value != "mobile_optimized" else (128, 128)
            texture = self._create_flow_texture(resolution, shader_config.parameters)

            return ShaderResource(
                name=shader_config.name,
                resource_type="flow_texture",
                data=texture,
                format="RGB",
                gpu_optimized=True
            )

        return None

    def _create_displacement_texture(self, resolution: Tuple[int, int], parameters: Dict[str, Any]) -> np.ndarray:
        """Create displacement texture"""
        height, width = resolution

        y, x = np.ogrid[:height, :width]
        center_y, center_x = height // 2, width // 2

        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        max_distance = min(width, height) // 2

        intensity = parameters.get("intensity", 0.8)
        displacement = intensity * (1.0 - distance / max_distance)
        displacement = np.clip(displacement, 0, 1)

        texture = np.zeros((height, width, 3), dtype=np.float32)
        texture[:, :, 0] = displacement
        texture[:, :, 1] = displacement
        texture[:, :, 2] = displacement

        return texture

    def _create_flow_texture(self, resolution: Tuple[int, int], parameters: Dict[str, Any]) -> np.ndarray:
        """Create flow texture"""
        height, width = resolution

        viscosity = parameters.get("viscosity", 0.7)
        flow_rate = parameters.get("flow_rate", 0.5)

        flow_x = self._generate_perlin_noise(width, height, scale=0.05) * flow_rate
        flow_y = self._generate_perlin_noise(width, height, scale=0.05, offset=1000) * flow_rate

        texture = np.zeros((height, width, 3), dtype=np.float32)
        texture[:, :, 0] = (flow_x + 1.0) * 0.5
        texture[:, :, 1] = (flow_y + 1.0) * 0.5
        texture[:, :, 2] = viscosity

        return texture

    def _generate_foley_triggers(self, foley_map: List[Any], brush_set: List[Any]) -> List[FoleyTrigger]:
        """Generate foley sound triggers"""
        foley_triggers = []

        for foley_mapping in foley_map:
            trigger = self._create_foley_trigger(foley_mapping)
            foley_triggers.append(trigger)

        return foley_triggers

    def _create_foley_trigger(self, foley_mapping: Any) -> FoleyTrigger:
        """Create a foley trigger from mapping"""
        brush_type = foley_mapping.brush_type
        sound_type = foley_mapping.sound_trigger

        intensity_curve = self._generate_intensity_curve(sound_type)
        pitch_range, volume_range = self._generate_pitch_volume_ranges(sound_type)
        variations = self._generate_sound_variations(sound_type)

        return FoleyTrigger(
            brush_type=brush_type,
            sound_type=sound_type,
            intensity_curve=intensity_curve,
            pitch_range=pitch_range,
            volume_range=volume_range,
            variations=variations
        )

    def _generate_intensity_curve(self, sound_type: str) -> List[float]:
        """Generate intensity curve for sound type"""
        if sound_type == "spring_twang":
            return [0.0, 0.2, 0.8, 1.0, 0.6, 0.2, 0.0]
        elif sound_type == "coil_bounce":
            return [0.0, 0.1, 0.9, 0.7, 0.3, 0.1, 0.0]
        elif sound_type == "slow_slurp":
            return [0.0, 0.3, 0.6, 0.8, 0.9, 0.7, 0.0]
        elif sound_type == "bubble_pop":
            return [0.0, 0.1, 0.3, 1.0, 0.8, 0.4, 0.0]
        else:
            return [0.0, 0.5, 1.0, 0.8, 0.3, 0.0]

    def _generate_pitch_volume_ranges(self, sound_type: str) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Generate pitch and volume ranges"""
        if sound_type in ["spring_twang", "coil_bounce"]:
            pitch_range = (0.8, 1.5)
            volume_range = (0.3, 0.9)
        elif sound_type in ["slow_slurp", "bubble_pop"]:
            pitch_range = (0.5, 1.2)
            volume_range = (0.2, 0.7)
        else:
            pitch_range = (0.7, 1.3)
            volume_range = (0.3, 0.8)

        return pitch_range, volume_range

    def _generate_sound_variations(self, sound_type: str) -> List[str]:
        """Generate sound variations"""
        base_variations = [f"{sound_type}_01", f"{sound_type}_02", f"{sound_type}_03"]

        if sound_type == "spring_twang":
            base_variations.extend([f"{sound_type}_high", f"{sound_type}_low"])
        elif sound_type == "bubble_pop":
            base_variations.extend([f"{sound_type}_small", f"{sound_type}_large"])

        return base_variations

    def _generate_animation_resources(self, animation_profile: Optional[Dict[str, Any]], performance_profile: Any) -> List[AnimationResource]:
        """Generate animation resources if needed"""
        animation_resources = []

        if not animation_profile:
            return animation_resources

        keyframe_count = int(animation_profile.get("frame_rate", 30) * animation_profile.get("duration", 5.0))
        keyframe_data = self._generate_keyframe_data(keyframe_count)

        animation_resources.append(AnimationResource(
            name="goo_animation_keyframes",
            resource_type="keyframe_structure",
            data=keyframe_data,
            keyframe_count=keyframe_count,
            duration=animation_profile.get("duration", 5.0)
        ))

        buffer_size = keyframe_count * 100
        stroke_buffer = self._generate_stroke_buffer(buffer_size)

        animation_resources.append(AnimationResource(
            name="stroke_recording_buffer",
            resource_type="stroke_buffer",
            data=stroke_buffer,
            keyframe_count=keyframe_count,
            duration=animation_profile.get("duration", 5.0)
        ))

        onion_layers = self._generate_onion_skin_layers(keyframe_count)

        animation_resources.append(AnimationResource(
            name="onion_skin_preview",
            resource_type="preview_layers",
            data=onion_layers,
            keyframe_count=keyframe_count,
            duration=animation_profile.get("duration", 5.0)
        ))

        return animation_resources

    def _generate_keyframe_data(self, keyframe_count: int) -> Dict[str, Any]:
        """Generate keyframe data structure"""
        keyframes = []
        for i in range(keyframe_count):
            keyframe = {
                "frame": i,
                "timestamp": i / 30.0,
                "brush_strokes": [],
                "deformation_state": {},
                "audio_events": []
            }
            keyframes.append(keyframe)

        return {"keyframes": keyframes}

    def _generate_stroke_buffer(self, buffer_size: int) -> Dict[str, Any]:
        """Generate stroke recording buffer"""
        return {
            "buffer_size": buffer_size,
            "strokes": [],
            "current_index": 0
        }

    def _generate_onion_skin_layers(self, keyframe_count: int) -> Dict[str, Any]:
        """Generate onion skin preview layers"""
        layers = []
        for i in range(min(5, keyframe_count)):
            layer = {
                "frame": i,
                "opacity": 0.3 - (i * 0.05),
                "data": None
            }
            layers.append(layer)

        return {"layers": layers}
