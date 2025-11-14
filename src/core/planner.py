"""
Clip duration planning and pacing engine for mov3.
Sophisticated algorithm for determining clip durations to match audio length.
"""

import random
from typing import List, Tuple, Dict
from dataclasses import dataclass

from ..utils.logger import Logger


@dataclass
class ClipPlan:
    """Represents a planned clip with duration."""
    index: int
    duration: float
    start_time: float  # Start time in the final video
    end_time: float    # End time in the final video


class DurationPlanner:
    """
    Plans clip durations to perfectly match audio duration.

    Features:
    - Min/max duration constraints
    - Overlap timing support
    - Soft budgeting (±25% adjacent duration smoothing)
    - Rounding corrections
    - Final error absorption for perfect match
    - Single-clip and multi-clip logic
    """

    def __init__(
        self,
        audio_duration: float,
        min_clip_duration: float = 2.0,
        max_clip_duration: float = 5.0,
        overlap_duration: float = 0.5,
        soft_budget_tolerance: float = 0.25
    ):
        """
        Initialize duration planner.

        Args:
            audio_duration: Total duration to match (seconds)
            min_clip_duration: Minimum duration per clip
            max_clip_duration: Maximum duration per clip
            overlap_duration: Overlap between clips for transitions
            soft_budget_tolerance: Tolerance for duration smoothing (±25%)
        """
        self.audio_duration = audio_duration
        self.min_clip = min_clip_duration
        self.max_clip = max_clip_duration
        self.overlap = overlap_duration
        self.tolerance = soft_budget_tolerance

        # Validate inputs
        if self.min_clip > self.max_clip:
            raise ValueError(f"min_clip ({self.min_clip}) cannot be greater than max_clip ({self.max_clip})")

        if self.audio_duration < self.min_clip:
            Logger.warning(f"Audio duration ({self.audio_duration}s) is less than min clip ({self.min_clip}s)")

        Logger.debug(
            f"DurationPlanner initialized: audio={audio_duration:.2f}s, "
            f"min={min_clip_duration:.2f}s, max={max_clip_duration:.2f}s, "
            f"overlap={overlap_duration:.2f}s"
        )

    def plan_clips(self) -> List[ClipPlan]:
        """
        Plan all clips to match the audio duration.

        Returns:
            List of ClipPlan objects with durations
        """
        # Calculate how many clips we need
        num_clips = self._estimate_clip_count()

        Logger.debug(f"Estimated clips needed: {num_clips}")

        if num_clips == 1:
            # Single clip case
            return self._plan_single_clip()
        else:
            # Multi-clip case
            return self._plan_multiple_clips(num_clips)

    def _estimate_clip_count(self) -> int:
        """
        Estimate how many clips are needed.

        Returns:
            Estimated number of clips
        """
        # Account for overlaps
        # Each clip contributes (duration - overlap) to total, except the last one
        # So: total_duration ≈ (n-1) * (avg_duration - overlap) + avg_duration
        # Simplified: total_duration ≈ n * avg_duration - (n-1) * overlap

        avg_duration = (self.min_clip + self.max_clip) / 2

        # Solve for n
        # audio_duration = n * avg_duration - (n-1) * overlap
        # audio_duration = n * avg_duration - n * overlap + overlap
        # audio_duration = n * (avg_duration - overlap) + overlap
        # n = (audio_duration - overlap) / (avg_duration - overlap)

        if avg_duration <= self.overlap:
            # Edge case: overlap is too large
            Logger.warning("Overlap duration is >= average clip duration, adjusting")
            return max(1, int(self.audio_duration / self.min_clip))

        n = (self.audio_duration - self.overlap) / (avg_duration - self.overlap)
        return max(1, int(n))

    def _plan_single_clip(self) -> List[ClipPlan]:
        """
        Plan for a single clip.

        Returns:
            List with one ClipPlan
        """
        duration = self.audio_duration

        # Clamp to min/max if needed
        if duration < self.min_clip:
            Logger.warning(f"Single clip duration ({duration:.2f}s) below minimum ({self.min_clip:.2f}s)")
            duration = self.min_clip
        elif duration > self.max_clip:
            Logger.warning(f"Single clip duration ({duration:.2f}s) above maximum ({self.max_clip:.2f}s)")
            duration = self.max_clip

        return [ClipPlan(
            index=0,
            duration=duration,
            start_time=0.0,
            end_time=duration
        )]

    def _plan_multiple_clips(self, num_clips: int) -> List[ClipPlan]:
        """
        Plan multiple clips with soft budgeting and error absorption.

        Args:
            num_clips: Target number of clips

        Returns:
            List of ClipPlan objects
        """
        # Calculate target average duration
        # total_time = sum(durations) - (n-1) * overlap
        target_sum = self.audio_duration + (num_clips - 1) * self.overlap
        target_avg = target_sum / num_clips

        Logger.debug(f"Target average duration: {target_avg:.2f}s")

        # Generate random durations within constraints
        durations = []
        for i in range(num_clips):
            # Random duration around target average
            min_d = max(self.min_clip, target_avg * (1 - self.tolerance))
            max_d = min(self.max_clip, target_avg * (1 + self.tolerance))

            # Ensure valid range
            if min_d > max_d:
                min_d = self.min_clip
                max_d = self.max_clip

            duration = random.uniform(min_d, max_d)
            durations.append(duration)

        Logger.debug(f"Initial durations (before correction): {[f'{d:.2f}' for d in durations]}")

        # Apply soft budgeting (smooth adjacent durations)
        durations = self._apply_soft_budgeting(durations)

        # Calculate current total accounting for overlaps
        current_total = sum(durations) - (num_clips - 1) * self.overlap
        error = self.audio_duration - current_total

        Logger.debug(f"Duration error before absorption: {error:.3f}s")

        # Absorb error across clips
        if abs(error) > 0.01:  # Only if significant error
            durations = self._absorb_error(durations, error)

        # Final adjustment: add/trim last clip if needed
        final_total = sum(durations) - (num_clips - 1) * self.overlap
        final_error = self.audio_duration - final_total

        if abs(final_error) > 0.01:
            Logger.debug(f"Final error adjustment needed: {final_error:.3f}s")
            durations[-1] += final_error
            durations[-1] = max(self.min_clip, min(self.max_clip, durations[-1]))

        # Create ClipPlan objects with timing
        plans = []
        current_time = 0.0

        for i, duration in enumerate(durations):
            plan = ClipPlan(
                index=i,
                duration=duration,
                start_time=current_time,
                end_time=current_time + duration
            )
            plans.append(plan)

            # Move to next clip start (accounting for overlap)
            current_time += duration - self.overlap

        Logger.debug(
            f"Final clip plan: {len(plans)} clips, "
            f"total={sum(d.duration for d in plans):.2f}s, "
            f"effective={sum(d.duration for d in plans) - (len(plans)-1)*self.overlap:.2f}s"
        )

        return plans

    def _apply_soft_budgeting(self, durations: List[float]) -> List[float]:
        """
        Apply soft budgeting to smooth adjacent clip durations.

        Args:
            durations: List of initial durations

        Returns:
            Smoothed durations
        """
        if len(durations) <= 1:
            return durations

        smoothed = durations.copy()

        # Smooth adjacent pairs
        for i in range(len(smoothed) - 1):
            current = smoothed[i]
            next_clip = smoothed[i + 1]

            # If difference is large, smooth them
            diff = abs(current - next_clip)
            avg = (current + next_clip) / 2

            if diff > avg * 0.5:  # If difference > 50% of average
                # Bring them closer together
                smoothed[i] = current * 0.7 + next_clip * 0.3
                smoothed[i + 1] = current * 0.3 + next_clip * 0.7

                # Clamp to constraints
                smoothed[i] = max(self.min_clip, min(self.max_clip, smoothed[i]))
                smoothed[i + 1] = max(self.min_clip, min(self.max_clip, smoothed[i + 1]))

        return smoothed

    def _absorb_error(self, durations: List[float], error: float) -> List[float]:
        """
        Distribute timing error across all clips.

        Args:
            durations: List of durations
            error: Error to distribute (positive = need more time, negative = need less)

        Returns:
            Adjusted durations
        """
        if len(durations) == 0:
            return durations

        # Distribute error evenly
        adjustment_per_clip = error / len(durations)

        adjusted = []
        for duration in durations:
            new_duration = duration + adjustment_per_clip

            # Clamp to constraints
            new_duration = max(self.min_clip, min(self.max_clip, new_duration))
            adjusted.append(new_duration)

        return adjusted

    def extend_last_clip(self, plans: List[ClipPlan], extension: float) -> List[ClipPlan]:
        """
        Extend the last clip by a given duration.

        Args:
            plans: Existing clip plans
            extension: Duration to add (seconds)

        Returns:
            Updated clip plans
        """
        if not plans:
            return plans

        plans[-1].duration += extension
        plans[-1].end_time += extension

        Logger.debug(f"Extended last clip by {extension:.2f}s to {plans[-1].duration:.2f}s")

        return plans

    def validate_plan(self, plans: List[ClipPlan]) -> Tuple[bool, str]:
        """
        Validate that a clip plan meets requirements.

        Args:
            plans: List of clip plans to validate

        Returns:
            (is_valid, error_message)
        """
        if not plans:
            return False, "No clips planned"

        # Check duration constraints
        for plan in plans:
            if plan.duration < self.min_clip * 0.9:  # Allow 10% tolerance
                return False, f"Clip {plan.index} duration ({plan.duration:.2f}s) below minimum"

            if plan.duration > self.max_clip * 1.1:  # Allow 10% tolerance
                return False, f"Clip {plan.index} duration ({plan.duration:.2f}s) above maximum"

        # Check total duration
        total_effective = sum(p.duration for p in plans) - (len(plans) - 1) * self.overlap
        error = abs(total_effective - self.audio_duration)

        if error > 1.0:  # Allow 1 second tolerance
            return False, f"Total duration mismatch: {error:.2f}s error"

        return True, "Valid"

    def get_summary(self, plans: List[ClipPlan]) -> Dict:
        """
        Get summary statistics for a plan.

        Args:
            plans: List of clip plans

        Returns:
            Dictionary with summary info
        """
        if not plans:
            return {}

        durations = [p.duration for p in plans]

        return {
            'num_clips': len(plans),
            'total_duration': sum(durations),
            'effective_duration': sum(durations) - (len(plans) - 1) * self.overlap,
            'min_duration': min(durations),
            'max_duration': max(durations),
            'avg_duration': sum(durations) / len(durations),
            'target_duration': self.audio_duration,
            'error': sum(durations) - (len(plans) - 1) * self.overlap - self.audio_duration
        }
