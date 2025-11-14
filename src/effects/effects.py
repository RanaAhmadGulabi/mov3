"""
Effects engine for mov3 video automation.
Handles pan, zoom, and combined effects for video clips.
"""

import random
from typing import Optional, Tuple, Dict, List
from enum import Enum
from dataclasses import dataclass

from ..utils.logger import Logger


class EffectType(Enum):
    """Types of effects available."""
    NONE = "none"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    PAN_UP = "pan_up"
    PAN_DOWN = "pan_down"
    KEN_BURNS_1 = "ken_burns_zoom_in_pan_right"
    KEN_BURNS_2 = "ken_burns_zoom_in_pan_left"
    KEN_BURNS_3 = "ken_burns_zoom_out_pan_right"
    KEN_BURNS_4 = "ken_burns_zoom_out_pan_left"
    ZOOM_IN_PAN_RIGHT = "zoom_in_pan_right"
    ZOOM_IN_PAN_LEFT = "zoom_in_pan_left"
    ZOOM_IN_PAN_UP = "zoom_in_pan_up"
    ZOOM_IN_PAN_DOWN = "zoom_in_pan_down"
    ZOOM_OUT_PAN_RIGHT = "zoom_out_pan_right"
    ZOOM_OUT_PAN_LEFT = "zoom_out_pan_left"
    ZOOM_OUT_PAN_UP = "zoom_out_pan_up"
    ZOOM_OUT_PAN_DOWN = "zoom_out_pan_down"


@dataclass
class EffectConfig:
    """Configuration for effects."""
    # Zoom settings
    zoom_in_min: float = 1.0
    zoom_in_max: float = 1.15
    zoom_out_min: float = 1.15
    zoom_out_max: float = 1.0

    # Pan settings (as percentage of frame)
    pan_amount: float = 0.10  # 10% of frame

    # Effect probabilities
    effect_probability: float = 0.75  # 75% of clips get effects

    # Anti-consecutive (don't use same effect twice in a row)
    anti_consecutive: bool = True


class EffectsEngine:
    """
    Generate pan and zoom effects for video clips.

    Creates FFmpeg zoompan filter strings for various effects.
    """

    def __init__(self, config: Optional[EffectConfig] = None):
        """
        Initialize effects engine.

        Args:
            config: Effect configuration
        """
        self.config = config or EffectConfig()
        self.last_effect: Optional[EffectType] = None

        # Available effects with weights (higher = more likely)
        self.effect_weights = {
            EffectType.NONE: 0.25,  # 25% chance of no effect
            EffectType.ZOOM_IN: 0.15,
            EffectType.ZOOM_OUT: 0.10,
            EffectType.PAN_LEFT: 0.08,
            EffectType.PAN_RIGHT: 0.08,
            EffectType.PAN_UP: 0.05,
            EffectType.PAN_DOWN: 0.05,
            EffectType.KEN_BURNS_1: 0.12,  # Ken Burns variants
            EffectType.KEN_BURNS_2: 0.12,
            EffectType.KEN_BURNS_3: 0.08,
            EffectType.KEN_BURNS_4: 0.08,
            EffectType.ZOOM_IN_PAN_RIGHT: 0.06,
            EffectType.ZOOM_IN_PAN_LEFT: 0.06,
            EffectType.ZOOM_IN_PAN_UP: 0.04,
            EffectType.ZOOM_IN_PAN_DOWN: 0.04,
            EffectType.ZOOM_OUT_PAN_RIGHT: 0.04,
            EffectType.ZOOM_OUT_PAN_LEFT: 0.04,
            EffectType.ZOOM_OUT_PAN_UP: 0.03,
            EffectType.ZOOM_OUT_PAN_DOWN: 0.03,
        }

        Logger.debug("EffectsEngine initialized")

    def select_random_effect(self) -> EffectType:
        """
        Select a random effect based on weights.

        Returns:
            Selected EffectType
        """
        # Get effects and weights
        effects = list(self.effect_weights.keys())
        weights = list(self.effect_weights.values())

        # If anti-consecutive, remove last effect from choices
        if self.config.anti_consecutive and self.last_effect:
            if self.last_effect in effects:
                idx = effects.index(self.last_effect)
                effects.pop(idx)
                weights.pop(idx)

                # Renormalize weights
                total = sum(weights)
                weights = [w / total for w in weights]

        # Select random effect
        selected = random.choices(effects, weights=weights, k=1)[0]
        self.last_effect = selected

        return selected

    def generate_filter(
        self,
        effect: EffectType,
        width: int,
        height: int,
        duration: float,
        fps: int = 30
    ) -> Optional[str]:
        """
        Generate FFmpeg zoompan filter string for the effect.

        Args:
            effect: Effect type to apply
            width: Video width
            height: Video height
            duration: Clip duration in seconds
            fps: Frames per second

        Returns:
            FFmpeg filter string, or None if no effect
        """
        if effect == EffectType.NONE:
            return None

        # Calculate total frames
        total_frames = int(duration * fps)

        # Generate filter based on effect type
        if effect == EffectType.ZOOM_IN:
            return self._zoom_in_filter(width, height, total_frames, fps)

        elif effect == EffectType.ZOOM_OUT:
            return self._zoom_out_filter(width, height, total_frames, fps)

        elif effect == EffectType.PAN_LEFT:
            return self._pan_filter(width, height, total_frames, fps, direction='left')

        elif effect == EffectType.PAN_RIGHT:
            return self._pan_filter(width, height, total_frames, fps, direction='right')

        elif effect == EffectType.PAN_UP:
            return self._pan_filter(width, height, total_frames, fps, direction='up')

        elif effect == EffectType.PAN_DOWN:
            return self._pan_filter(width, height, total_frames, fps, direction='down')

        # Ken Burns variants (zoom + pan)
        elif effect == EffectType.KEN_BURNS_1:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='in', pan='right')

        elif effect == EffectType.KEN_BURNS_2:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='in', pan='left')

        elif effect == EffectType.KEN_BURNS_3:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='out', pan='right')

        elif effect == EffectType.KEN_BURNS_4:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='out', pan='left')

        # Other combinations
        elif effect == EffectType.ZOOM_IN_PAN_RIGHT:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='in', pan='right')

        elif effect == EffectType.ZOOM_IN_PAN_LEFT:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='in', pan='left')

        elif effect == EffectType.ZOOM_IN_PAN_UP:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='in', pan='up')

        elif effect == EffectType.ZOOM_IN_PAN_DOWN:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='in', pan='down')

        elif effect == EffectType.ZOOM_OUT_PAN_RIGHT:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='out', pan='right')

        elif effect == EffectType.ZOOM_OUT_PAN_LEFT:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='out', pan='left')

        elif effect == EffectType.ZOOM_OUT_PAN_UP:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='out', pan='up')

        elif effect == EffectType.ZOOM_OUT_PAN_DOWN:
            return self._ken_burns_filter(width, height, total_frames, fps, zoom='out', pan='down')

        return None

    def _zoom_in_filter(self, width: int, height: int, frames: int, fps: int) -> str:
        """Generate zoom-in filter."""
        zoom_start = self.config.zoom_in_min
        zoom_end = self.config.zoom_in_max

        # Linear interpolation: start + (end - start) * progress
        # on = output frame number, frames = total frames
        return (
            f"zoompan="
            f"z='{zoom_start}+({zoom_end}-{zoom_start})*on/{frames}':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={frames}:"
            f"s={width}x{height}:"
            f"fps={fps}"
        )

    def _zoom_out_filter(self, width: int, height: int, frames: int, fps: int) -> str:
        """Generate zoom-out filter."""
        zoom_start = self.config.zoom_out_min
        zoom_end = self.config.zoom_out_max

        # Linear interpolation from start (zoomed in) to end (normal)
        return (
            f"zoompan="
            f"z='{zoom_start}+({zoom_end}-{zoom_start})*on/{frames}':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={frames}:"
            f"s={width}x{height}:"
            f"fps={fps}"
        )

    def _pan_filter(
        self,
        width: int,
        height: int,
        frames: int,
        fps: int,
        direction: str
    ) -> str:
        """Generate pan filter."""
        pan_amount = self.config.pan_amount

        # Center positions
        center_x = "iw/2-(iw/zoom/2)"
        center_y = "ih/2-(ih/zoom/2)"

        # Pan offset (pixels to pan)
        pan_pixels_x = f"{pan_amount}*iw"
        pan_pixels_y = f"{pan_amount}*ih"

        if direction == 'left':
            # Start right, move left: start at +pan, end at -pan
            x_expr = f"'({center_x})+{pan_pixels_x}*(1-2*on/{frames})'"
            y_expr = f"'{center_y}'"

        elif direction == 'right':
            # Start left, move right: start at -pan, end at +pan
            x_expr = f"'({center_x})+{pan_pixels_x}*(2*on/{frames}-1)'"
            y_expr = f"'{center_y}'"

        elif direction == 'up':
            # Start bottom, move up: start at +pan, end at -pan
            x_expr = f"'{center_x}'"
            y_expr = f"'({center_y})+{pan_pixels_y}*(1-2*on/{frames})'"

        else:  # down
            # Start top, move down: start at -pan, end at +pan
            x_expr = f"'{center_x}'"
            y_expr = f"'({center_y})+{pan_pixels_y}*(2*on/{frames}-1)'"

        return (
            f"zoompan="
            f"z='1.0':"
            f"x={x_expr}:"
            f"y={y_expr}:"
            f"d={frames}:"
            f"s={width}x{height}:"
            f"fps={fps}"
        )

    def _ken_burns_filter(
        self,
        width: int,
        height: int,
        frames: int,
        fps: int,
        zoom: str,
        pan: str
    ) -> str:
        """Generate Ken Burns (zoom + pan) filter."""
        pan_amount = self.config.pan_amount

        # Center positions
        center_x = "iw/2-(iw/zoom/2)"
        center_y = "ih/2-(ih/zoom/2)"

        # Pan offset (pixels to pan)
        pan_pixels_x = f"{pan_amount}*iw"
        pan_pixels_y = f"{pan_amount}*ih"

        # Zoom settings - linear interpolation
        if zoom == 'in':
            zoom_start = self.config.zoom_in_min
            zoom_end = self.config.zoom_in_max
            zoom_expr = f"'{zoom_start}+({zoom_end}-{zoom_start})*on/{frames}'"
        else:  # zoom out
            zoom_start = self.config.zoom_out_min
            zoom_end = self.config.zoom_out_max
            zoom_expr = f"'{zoom_start}+({zoom_end}-{zoom_start})*on/{frames}'"

        # Pan settings
        if pan == 'left':
            # Start right, move left
            x_expr = f"'({center_x})+{pan_pixels_x}*(1-2*on/{frames})'"
            y_expr = f"'{center_y}'"

        elif pan == 'right':
            # Start left, move right
            x_expr = f"'({center_x})+{pan_pixels_x}*(2*on/{frames}-1)'"
            y_expr = f"'{center_y}'"

        elif pan == 'up':
            # Start bottom, move up
            x_expr = f"'{center_x}'"
            y_expr = f"'({center_y})+{pan_pixels_y}*(1-2*on/{frames})'"

        else:  # down
            # Start top, move down
            x_expr = f"'{center_x}'"
            y_expr = f"'({center_y})+{pan_pixels_y}*(2*on/{frames}-1)'"

        return (
            f"zoompan="
            f"z={zoom_expr}:"
            f"x={x_expr}:"
            f"y={y_expr}:"
            f"d={frames}:"
            f"s={width}x{height}:"
            f"fps={fps}"
        )

    def get_effect_name(self, effect: EffectType) -> str:
        """Get human-readable effect name."""
        names = {
            EffectType.NONE: "None",
            EffectType.ZOOM_IN: "Zoom In",
            EffectType.ZOOM_OUT: "Zoom Out",
            EffectType.PAN_LEFT: "Pan Left",
            EffectType.PAN_RIGHT: "Pan Right",
            EffectType.PAN_UP: "Pan Up",
            EffectType.PAN_DOWN: "Pan Down",
            EffectType.KEN_BURNS_1: "Ken Burns (Zoom In + Pan Right)",
            EffectType.KEN_BURNS_2: "Ken Burns (Zoom In + Pan Left)",
            EffectType.KEN_BURNS_3: "Ken Burns (Zoom Out + Pan Right)",
            EffectType.KEN_BURNS_4: "Ken Burns (Zoom Out + Pan Left)",
            EffectType.ZOOM_IN_PAN_RIGHT: "Zoom In + Pan Right",
            EffectType.ZOOM_IN_PAN_LEFT: "Zoom In + Pan Left",
            EffectType.ZOOM_IN_PAN_UP: "Zoom In + Pan Up",
            EffectType.ZOOM_IN_PAN_DOWN: "Zoom In + Pan Down",
            EffectType.ZOOM_OUT_PAN_RIGHT: "Zoom Out + Pan Right",
            EffectType.ZOOM_OUT_PAN_LEFT: "Zoom Out + Pan Left",
            EffectType.ZOOM_OUT_PAN_UP: "Zoom Out + Pan Up",
            EffectType.ZOOM_OUT_PAN_DOWN: "Zoom Out + Pan Down",
        }
        return names.get(effect, "Unknown")
