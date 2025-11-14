"""
Transition engine for mov3 video automation.
Handles transitions between video clips.
"""

import random
from typing import Optional, List
from enum import Enum
from dataclasses import dataclass

from ..utils.logger import Logger


class TransitionType(Enum):
    """Types of transitions available."""
    CUT = "cut"  # No transition
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"


@dataclass
class TransitionConfig:
    """Configuration for transitions."""
    # Transition duration in seconds
    default_duration: float = 0.5

    # Transition probabilities
    transition_weights: dict = None

    # Anti-consecutive (don't use same transition twice in a row)
    anti_consecutive: bool = True

    def __post_init__(self):
        if self.transition_weights is None:
            # Default weights for transitions
            self.transition_weights = {
                TransitionType.FADE: 0.35,  # 35% - most common
                TransitionType.DISSOLVE: 0.25,  # 25%
                TransitionType.CUT: 0.15,  # 15% - simple cut
                TransitionType.WIPE_LEFT: 0.05,
                TransitionType.WIPE_RIGHT: 0.05,
                TransitionType.WIPE_UP: 0.025,
                TransitionType.WIPE_DOWN: 0.025,
                TransitionType.SLIDE_LEFT: 0.05,
                TransitionType.SLIDE_RIGHT: 0.05,
                TransitionType.SLIDE_UP: 0.025,
                TransitionType.SLIDE_DOWN: 0.025,
            }


class TransitionEngine:
    """
    Generate transitions between video clips.

    Creates FFmpeg xfade filter strings for various transitions.
    """

    def __init__(self, config: Optional[TransitionConfig] = None):
        """
        Initialize transition engine.

        Args:
            config: Transition configuration
        """
        self.config = config or TransitionConfig()
        self.last_transition: Optional[TransitionType] = None

        Logger.debug("TransitionEngine initialized")

    def select_random_transition(self) -> TransitionType:
        """
        Select a random transition based on weights.

        Returns:
            Selected TransitionType
        """
        # Get transitions and weights
        transitions = list(self.config.transition_weights.keys())
        weights = list(self.config.transition_weights.values())

        # If anti-consecutive, remove last transition from choices
        if self.config.anti_consecutive and self.last_transition:
            if self.last_transition in transitions:
                idx = transitions.index(self.last_transition)
                transitions.pop(idx)
                weights.pop(idx)

                # Renormalize weights
                total = sum(weights)
                if total > 0:
                    weights = [w / total for w in weights]

        # Select random transition
        selected = random.choices(transitions, weights=weights, k=1)[0]
        self.last_transition = selected

        return selected

    def get_xfade_transition(self, transition: TransitionType) -> Optional[str]:
        """
        Get xfade transition name for FFmpeg.

        Args:
            transition: Transition type

        Returns:
            xfade transition name, or None for CUT
        """
        if transition == TransitionType.CUT:
            return None

        # Map our transitions to xfade transition names
        xfade_map = {
            TransitionType.FADE: "fade",
            TransitionType.DISSOLVE: "dissolve",
            TransitionType.WIPE_LEFT: "wipeleft",
            TransitionType.WIPE_RIGHT: "wiperight",
            TransitionType.WIPE_UP: "wipeup",
            TransitionType.WIPE_DOWN: "wipedown",
            TransitionType.SLIDE_LEFT: "slideleft",
            TransitionType.SLIDE_RIGHT: "slideright",
            TransitionType.SLIDE_UP: "slideup",
            TransitionType.SLIDE_DOWN: "slidedown",
        }

        return xfade_map.get(transition)

    def build_xfade_filter(
        self,
        transition: TransitionType,
        offset: float,
        duration: Optional[float] = None
    ) -> Optional[str]:
        """
        Build xfade filter string for FFmpeg.

        Args:
            transition: Transition type
            offset: Offset time when transition starts
            duration: Transition duration (uses config default if not specified)

        Returns:
            xfade filter string, or None for CUT
        """
        if transition == TransitionType.CUT:
            return None

        xfade_name = self.get_xfade_transition(transition)
        if not xfade_name:
            return None

        trans_duration = duration or self.config.default_duration

        return f"xfade=transition={xfade_name}:duration={trans_duration}:offset={offset}"

    def build_concat_with_transitions(
        self,
        clip_durations: List[float],
        transitions: Optional[List[TransitionType]] = None,
        transition_duration: Optional[float] = None
    ) -> str:
        """
        Build complex filter for concatenating clips with transitions.

        Args:
            clip_durations: List of clip durations
            transitions: List of transitions (one less than clips). If None, random
            transition_duration: Override transition duration

        Returns:
            FFmpeg complex filter string
        """
        num_clips = len(clip_durations)

        if num_clips < 2:
            # Can't have transitions with less than 2 clips
            return ""

        # Generate random transitions if not provided
        if transitions is None:
            transitions = [self.select_random_transition() for _ in range(num_clips - 1)]

        # Ensure we have the right number of transitions
        if len(transitions) != num_clips - 1:
            Logger.warning(f"Expected {num_clips - 1} transitions, got {len(transitions)}")
            transitions = transitions[:num_clips - 1]

        trans_dur = transition_duration or self.config.default_duration

        # Build filter complex
        # This is complex because xfade requires specific input ordering
        filter_parts = []
        current_offset = 0.0

        for i in range(num_clips - 1):
            transition = transitions[i]
            xfade_name = self.get_xfade_transition(transition)

            if xfade_name:
                # Calculate offset (when second clip starts)
                current_offset += clip_durations[i] - trans_dur

                if i == 0:
                    # First transition
                    filter_parts.append(
                        f"[0:v][1:v]xfade=transition={xfade_name}:"
                        f"duration={trans_dur}:offset={current_offset}[v01]"
                    )
                else:
                    # Subsequent transitions
                    prev_label = f"v0{i}" if i == 1 else f"v{i-1}{i}"
                    curr_label = f"v{i}{i+1}"
                    filter_parts.append(
                        f"[{prev_label}][{i+1}:v]xfade=transition={xfade_name}:"
                        f"duration={trans_dur}:offset={current_offset}[{curr_label}]"
                    )
            else:
                # CUT - no transition, just concat
                current_offset += clip_durations[i]

        return ";".join(filter_parts)

    def get_transition_name(self, transition: TransitionType) -> str:
        """Get human-readable transition name."""
        names = {
            TransitionType.CUT: "Cut (No Transition)",
            TransitionType.FADE: "Fade",
            TransitionType.DISSOLVE: "Dissolve",
            TransitionType.WIPE_LEFT: "Wipe Left",
            TransitionType.WIPE_RIGHT: "Wipe Right",
            TransitionType.WIPE_UP: "Wipe Up",
            TransitionType.WIPE_DOWN: "Wipe Down",
            TransitionType.SLIDE_LEFT: "Slide Left",
            TransitionType.SLIDE_RIGHT: "Slide Right",
            TransitionType.SLIDE_UP: "Slide Up",
            TransitionType.SLIDE_DOWN: "Slide Down",
        }
        return names.get(transition, "Unknown")
