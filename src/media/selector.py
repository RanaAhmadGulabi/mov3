"""
Media selection engine for mov3.
Handles selecting and planning media files for video composition.
"""

import os
import random
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import Logger


class MediaType(Enum):
    """Type of media file."""
    IMAGE = "image"
    VIDEO = "video"


class SelectionMode(Enum):
    """Mode for selecting media files."""
    SEQUENTIAL = "sequential"
    RANDOM = "random"


@dataclass
class MediaFile:
    """Represents a media file with metadata."""
    path: Path
    type: MediaType
    duration: Optional[float] = None  # For videos
    used_segments: List[Tuple[float, float]] = None  # Track used video segments
    reuse_count: int = 0  # Track how many times this file has been reused

    def __post_init__(self):
        if self.used_segments is None:
            self.used_segments = []


@dataclass
class MediaSelection:
    """Result of media selection with planned durations."""
    file: MediaFile
    duration: float
    start_time: Optional[float] = None  # For video clips
    end_time: Optional[float] = None
    variation: Optional[Dict] = None  # Variation parameters for reuse


class MediaSelector:
    """
    Selects and manages media files for video composition.

    Features:
    - Sequential or random selection
    - Anti-consecutive duplicate filter
    - Media expansion when pool is too small
    - Variation system for reused media
    - Video segment tracking to avoid reusing same portions
    """

    def __init__(
        self,
        media_dir: Path,
        audio_name: str,
        mode: SelectionMode = SelectionMode.SEQUENTIAL,
        anti_consecutive: bool = True,
        image_formats: List[str] = None,
        video_formats: List[str] = None
    ):
        """
        Initialize media selector.

        Args:
            media_dir: Directory containing media subfolders
            audio_name: Name of audio file (without extension)
            mode: Selection mode (sequential or random)
            anti_consecutive: Prevent same file appearing consecutively
            image_formats: List of supported image extensions
            video_formats: List of supported video extensions
        """
        self.media_dir = Path(media_dir)
        self.audio_name = audio_name
        self.mode = mode
        self.anti_consecutive = anti_consecutive

        # Default supported formats
        self.image_formats = image_formats or ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
        self.video_formats = video_formats or ['.mp4', '.mov', '.avi', '.mkv', '.webm']

        # Media pool
        self.media_files: List[MediaFile] = []
        self.current_index = 0
        self.last_selected: Optional[MediaFile] = None

        # Load media files
        self._load_media()

        Logger.info(f"MediaSelector initialized: {len(self.media_files)} files found")

    def _load_media(self):
        """Load media files from the appropriate subfolder."""
        # Look for subfolder matching audio name
        media_folder = self.media_dir / self.audio_name

        if not media_folder.exists():
            Logger.warning(f"Media folder not found: {media_folder}")
            return

        # Scan for media files
        for file_path in sorted(media_folder.iterdir()):
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()

            if ext in self.image_formats:
                self.media_files.append(MediaFile(
                    path=file_path,
                    type=MediaType.IMAGE
                ))
            elif ext in self.video_formats:
                # For videos, we'll need to get duration later
                self.media_files.append(MediaFile(
                    path=file_path,
                    type=MediaType.VIDEO
                ))

        # Check if files are numerically named for sequential mode
        if self.mode == SelectionMode.SEQUENTIAL:
            if not self._is_numeric_naming():
                Logger.info("Media files not numerically named, using found order")

        # Shuffle if random mode
        if self.mode == SelectionMode.RANDOM:
            random.shuffle(self.media_files)
            Logger.info("Media files shuffled for random selection")

    def _is_numeric_naming(self) -> bool:
        """Check if media files follow numeric naming (e.g., 001.jpg, 002.jpg)."""
        if not self.media_files:
            return False

        numeric_count = 0
        for media_file in self.media_files:
            name = media_file.path.stem
            if name.isdigit():
                numeric_count += 1

        return numeric_count / len(self.media_files) > 0.7  # 70% threshold

    def get_media_count(self) -> int:
        """Get total number of available media files."""
        return len(self.media_files)

    def has_sufficient_media(self, required_count: int) -> bool:
        """
        Check if there are enough media files for the job.

        Args:
            required_count: Number of clips needed

        Returns:
            True if sufficient media available
        """
        return len(self.media_files) >= required_count

    def estimate_required_clips(
        self,
        audio_duration: float,
        min_clip_duration: float,
        max_clip_duration: float
    ) -> int:
        """
        Estimate how many clips will be needed.

        Args:
            audio_duration: Total audio duration in seconds
            min_clip_duration: Minimum clip duration
            max_clip_duration: Maximum clip duration

        Returns:
            Estimated number of clips needed
        """
        # Use average duration for estimation
        avg_duration = (min_clip_duration + max_clip_duration) / 2
        return int(audio_duration / avg_duration) + 1

    def select_next(
        self,
        duration: float,
        avoid_file: Optional[MediaFile] = None
    ) -> MediaSelection:
        """
        Select the next media file.

        Args:
            duration: Desired duration for this clip
            avoid_file: File to avoid (for anti-consecutive)

        Returns:
            MediaSelection with file and parameters
        """
        if not self.media_files:
            raise ValueError("No media files available")

        selected_file = None

        if self.mode == SelectionMode.SEQUENTIAL:
            # Sequential selection with wrap-around
            attempts = 0
            while attempts < len(self.media_files):
                candidate = self.media_files[self.current_index]

                # Check anti-consecutive
                if self.anti_consecutive and avoid_file and candidate == avoid_file:
                    self.current_index = (self.current_index + 1) % len(self.media_files)
                    attempts += 1
                    continue

                selected_file = candidate
                self.current_index = (self.current_index + 1) % len(self.media_files)
                break

            if selected_file is None:
                # Fallback if we can't avoid the file (only one file available)
                selected_file = self.media_files[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.media_files)

        else:  # RANDOM mode
            # Random selection with anti-consecutive
            if len(self.media_files) == 1:
                selected_file = self.media_files[0]
            else:
                attempts = 0
                max_attempts = 50

                while attempts < max_attempts:
                    candidate = random.choice(self.media_files)

                    if self.anti_consecutive and avoid_file and candidate == avoid_file:
                        attempts += 1
                        continue

                    selected_file = candidate
                    break

                if selected_file is None:
                    # Fallback
                    selected_file = random.choice(self.media_files)

        # Track reuse
        selected_file.reuse_count += 1

        # Create selection
        selection = MediaSelection(
            file=selected_file,
            duration=duration
        )

        # Handle video segment selection
        if selected_file.type == MediaType.VIDEO:
            self._plan_video_segment(selection)

        # Add variation if file is being reused
        if selected_file.reuse_count > 1:
            selection.variation = self._generate_variation()

        self.last_selected = selected_file
        return selection

    def _plan_video_segment(self, selection: MediaSelection):
        """
        Plan which segment of a video to use.

        Args:
            selection: MediaSelection to update with start/end times
        """
        # TODO: Get actual video duration (requires ffprobe)
        # For now, assume videos are long enough
        video_duration = selection.file.duration or 30.0  # Default assumption

        desired_duration = selection.duration
        used_segments = selection.file.used_segments

        # Find available segment
        if not used_segments:
            # First use - start from random position
            max_start = max(0, video_duration - desired_duration)
            start_time = random.uniform(0, max_start) if max_start > 0 else 0
        else:
            # Try to find unused segment
            # For now, simple approach: pick random segment not yet used
            available_duration = video_duration
            for used_start, used_end in used_segments:
                available_duration -= (used_end - used_start)

            if available_duration >= desired_duration:
                # Find gap or unused portion
                start_time = self._find_available_video_segment(
                    video_duration,
                    desired_duration,
                    used_segments
                )
            else:
                # Reuse existing segment with offset
                start_time = random.uniform(0, max(0, video_duration - desired_duration))

        end_time = min(start_time + desired_duration, video_duration)

        selection.start_time = start_time
        selection.end_time = end_time

        # Track used segment
        selection.file.used_segments.append((start_time, end_time))

    def _find_available_video_segment(
        self,
        total_duration: float,
        needed_duration: float,
        used_segments: List[Tuple[float, float]]
    ) -> float:
        """
        Find an available (unused) segment in a video.

        Args:
            total_duration: Total video duration
            needed_duration: Duration needed
            used_segments: List of (start, end) tuples of used segments

        Returns:
            Start time for new segment
        """
        # Sort used segments
        sorted_segments = sorted(used_segments)

        # Check gaps between used segments
        last_end = 0
        for start, end in sorted_segments:
            gap = start - last_end
            if gap >= needed_duration:
                # Found a gap
                return last_end
            last_end = end

        # Check end of video
        final_gap = total_duration - last_end
        if final_gap >= needed_duration:
            return last_end

        # No available segment, return random
        return random.uniform(0, max(0, total_duration - needed_duration))

    def _generate_variation(self) -> Dict:
        """
        Generate variation parameters for reused media.

        Returns:
            Dictionary with variation parameters
        """
        return {
            'zoom': random.uniform(0.95, 1.15),
            'position_offset_x': random.uniform(-0.1, 0.1),
            'position_offset_y': random.uniform(-0.1, 0.1),
            'brightness': random.uniform(-0.1, 0.1),
            'flip_horizontal': random.random() < 0.2,
            'flip_vertical': False  # Usually don't flip vertically
        }

    def get_statistics(self) -> Dict:
        """Get statistics about media usage."""
        stats = {
            'total_files': len(self.media_files),
            'images': sum(1 for m in self.media_files if m.type == MediaType.IMAGE),
            'videos': sum(1 for m in self.media_files if m.type == MediaType.VIDEO),
            'reuse_stats': {}
        }

        for media_file in self.media_files:
            if media_file.reuse_count > 0:
                stats['reuse_stats'][str(media_file.path.name)] = media_file.reuse_count

        return stats

    def reset(self):
        """Reset selector state (for new job)."""
        self.current_index = 0
        self.last_selected = None

        for media_file in self.media_files:
            media_file.reuse_count = 0
            media_file.used_segments = []

        if self.mode == SelectionMode.RANDOM:
            random.shuffle(self.media_files)
