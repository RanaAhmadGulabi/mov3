"""
FFmpeg orchestration layer for mov3.
Handles all FFmpeg operations: encoding, scaling, transitions, concatenation.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..utils.logger import Logger


@dataclass
class FFmpegCapabilities:
    """Detected FFmpeg capabilities."""
    has_nvenc: bool = False
    has_amf: bool = False
    has_videotoolbox: bool = False
    version: str = ""
    available_encoders: List[str] = None

    def __post_init__(self):
        if self.available_encoders is None:
            self.available_encoders = []


class FFmpegOrchestrator:
    """
    Orchestrates all FFmpeg operations for video generation.

    Features:
    - Hardware encoder detection and fallback
    - Multi-clip xfade chain building
    - Smart scaling filters
    - Audio/video muxing
    - Subtitle filter support
    - Pre-flight checks
    - User-friendly error messages
    """

    def __init__(self, temp_dir: str = "temp"):
        """
        Initialize FFmpeg orchestrator.

        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Check FFmpeg availability
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()

        if not self.ffmpeg_path:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg and add to PATH.")

        # Detect capabilities
        self.capabilities = self._detect_capabilities()

        Logger.info(f"FFmpeg initialized: {self.capabilities.version}")
        Logger.info(
            f"Hardware encoders: "
            f"NVENC={self.capabilities.has_nvenc}, "
            f"AMF={self.capabilities.has_amf}, "
            f"VideoToolbox={self.capabilities.has_videotoolbox}"
        )

    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable."""
        return shutil.which("ffmpeg")

    def _find_ffprobe(self) -> Optional[str]:
        """Find FFprobe executable."""
        return shutil.which("ffprobe")

    def _detect_capabilities(self) -> FFmpegCapabilities:
        """
        Detect FFmpeg capabilities and available encoders.

        Returns:
            FFmpegCapabilities object
        """
        caps = FFmpegCapabilities()

        try:
            # Get version
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                first_line = result.stdout.split('\n')[0]
                caps.version = first_line.replace("ffmpeg version ", "").split()[0]

            # Check available encoders
            result = subprocess.run(
                [self.ffmpeg_path, "-encoders"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                output = result.stdout

                # Check for hardware encoders
                caps.has_nvenc = "h264_nvenc" in output or "nvenc_h264" in output
                caps.has_amf = "h264_amf" in output
                caps.has_videotoolbox = "h264_videotoolbox" in output

                # Parse available encoders
                for line in output.split('\n'):
                    if "h264" in line.lower() or "hevc" in line.lower():
                        parts = line.split()
                        if len(parts) >= 2 and parts[0] in ['V.....', 'V....D']:
                            caps.available_encoders.append(parts[1])

        except Exception as e:
            Logger.error(f"Error detecting FFmpeg capabilities: {e}")

        return caps

    def select_encoder(
        self,
        preferred_encoders: List[str],
        fallback: str = "libx264"
    ) -> str:
        """
        Select the best available encoder.

        Args:
            preferred_encoders: List of encoders in order of preference
            fallback: Fallback encoder if none of preferred are available

        Returns:
            Selected encoder name
        """
        for encoder in preferred_encoders:
            if encoder == "h264_nvenc" and self.capabilities.has_nvenc:
                Logger.info(f"Using NVENC hardware encoder")
                return encoder
            elif encoder == "h264_amf" and self.capabilities.has_amf:
                Logger.info(f"Using AMF hardware encoder")
                return encoder
            elif encoder == "h264_videotoolbox" and self.capabilities.has_videotoolbox:
                Logger.info(f"Using VideoToolbox hardware encoder")
                return encoder

        Logger.info(f"Using fallback encoder: {fallback}")
        return fallback

    def get_media_info(self, file_path: str) -> Dict:
        """
        Get media file information using ffprobe.

        Args:
            file_path: Path to media file

        Returns:
            Dictionary with media info (duration, resolution, codec, etc.)
        """
        if not self.ffprobe_path:
            Logger.error("ffprobe not found")
            return {}

        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                Logger.error(f"ffprobe failed for {file_path}: {result.stderr}")
                return {}

            import json
            data = json.loads(result.stdout)

            # Extract useful info
            info = {}

            if "format" in data:
                info["duration"] = float(data["format"].get("duration", 0))
                info["size"] = int(data["format"].get("size", 0))
                info["bitrate"] = int(data["format"].get("bit_rate", 0))

            # Find video stream
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info["width"] = stream.get("width", 0)
                    info["height"] = stream.get("height", 0)
                    info["codec"] = stream.get("codec_name", "")
                    info["fps"] = self._parse_fps(stream.get("r_frame_rate", "30/1"))
                    info["aspect_ratio"] = f"{stream.get('display_aspect_ratio', 'N/A')}"
                    break

            return info

        except Exception as e:
            Logger.error(f"Error getting media info for {file_path}: {e}")
            return {}

    def _parse_fps(self, fps_str: str) -> float:
        """Parse FPS from string like '30/1' or '30000/1001'."""
        try:
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return float(num) / float(den)
            return float(fps_str)
        except:
            return 30.0

    def encode_image_clip(
        self,
        image_path: str,
        output_path: str,
        duration: float,
        resolution: Tuple[int, int] = (1920, 1080),
        fps: int = 30,
        codec: str = "libx264",
        preset: str = "medium",
        crf: int = 23,
        filters: Optional[List[str]] = None,
        effect_filter: Optional[str] = None
    ) -> bool:
        """
        Encode an image into a video clip.

        Args:
            image_path: Path to input image
            output_path: Path for output video
            duration: Duration in seconds
            resolution: (width, height) tuple
            fps: Frames per second
            codec: Video codec
            preset: Encoding preset
            crf: Constant Rate Factor (quality)
            filters: Additional FFmpeg filters
            effect_filter: Effect filter (e.g., zoompan) - applied BEFORE scaling

        Returns:
            True if successful
        """
        try:
            width, height = resolution

            # Build filter chain
            filter_parts = []

            # Apply effect first if provided (zoompan works on original image)
            if effect_filter:
                filter_parts.append(effect_filter)
            else:
                # If no effect, need to scale and crop
                filter_parts.append(f"scale={width}:{height}:force_original_aspect_ratio=increase")
                filter_parts.append(f"crop={width}:{height}")

            # Add any additional filters
            if filters:
                filter_parts.extend(filters)

            filter_str = ",".join(filter_parts)

            cmd = [
                self.ffmpeg_path,
                "-loop", "1",
                "-i", image_path,
                "-t", str(duration),
                "-vf", filter_str,
                "-r", str(fps),
                "-c:v", codec,
                "-preset", preset,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-y",
                output_path
            ]

            Logger.debug(f"Encoding image clip with filter: {filter_str}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )

            if result.returncode != 0:
                Logger.error(f"FFmpeg encode failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            Logger.error(f"Error encoding image clip: {e}")
            return False

    def encode_video_clip(
        self,
        video_path: str,
        output_path: str,
        start_time: float,
        duration: float,
        resolution: Tuple[int, int] = (1920, 1080),
        fps: int = 30,
        codec: str = "libx264",
        preset: str = "medium",
        crf: int = 23,
        filters: Optional[List[str]] = None,
        effect_filter: Optional[str] = None
    ) -> bool:
        """
        Extract and encode a video clip segment.

        Args:
            video_path: Path to input video
            output_path: Path for output video
            start_time: Start time in seconds
            duration: Duration in seconds
            resolution: (width, height) tuple
            fps: Frames per second
            codec: Video codec
            preset: Encoding preset
            crf: Constant Rate Factor
            filters: Additional FFmpeg filters
            effect_filter: Effect filter (e.g., zoompan) - applied BEFORE scaling

        Returns:
            True if successful
        """
        try:
            width, height = resolution

            # Build filter chain
            filter_parts = []

            # Apply effect first if provided
            if effect_filter:
                filter_parts.append(effect_filter)
            else:
                # If no effect, need to scale and crop
                filter_parts.append(f"scale={width}:{height}:force_original_aspect_ratio=increase")
                filter_parts.append(f"crop={width}:{height}")

            # Add any additional filters
            if filters:
                filter_parts.extend(filters)

            filter_str = ",".join(filter_parts)

            cmd = [
                self.ffmpeg_path,
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(duration),
                "-vf", filter_str,
                "-r", str(fps),
                "-c:v", codec,
                "-preset", preset,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-y",
                output_path
            ]

            Logger.debug(f"Encoding video clip with filter: {filter_str}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                Logger.error(f"FFmpeg encode failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            Logger.error(f"Error encoding video clip: {e}")
            return False

    def concatenate_clips(
        self,
        clip_paths: List[str],
        output_path: str,
        audio_path: Optional[str] = None,
        transition_duration: float = 0.5,
        transitions: Optional[List[str]] = None
    ) -> bool:
        """
        Concatenate multiple clips with transitions.

        Args:
            clip_paths: List of paths to video clips
            output_path: Output file path
            audio_path: Optional audio file to mux
            transition_duration: Duration of crossfade transitions
            transitions: List of xfade transition names (e.g., ['fade', 'dissolve'])
                        If None, uses 'fade' for all. One per transition (len = clips - 1)

        Returns:
            True if successful
        """
        if not clip_paths:
            Logger.error("No clips to concatenate")
            return False

        try:
            if len(clip_paths) == 1:
                # Single clip: just mux with audio
                return self._simple_concat(clip_paths[0], output_path, audio_path)
            elif transition_duration == 0:
                # No transitions requested: simple concat
                return self._simple_concat_multiple(clip_paths, output_path, audio_path)
            else:
                # Use xfade transitions
                return self._xfade_concat(clip_paths, output_path, audio_path, transition_duration, transitions)

        except Exception as e:
            Logger.error(f"Error concatenating clips: {e}")
            return False

    def _simple_concat(
        self,
        clip_path: str,
        output_path: str,
        audio_path: Optional[str] = None
    ) -> bool:
        """Simple concatenation (single clip or no transitions)."""
        try:
            if audio_path:
                # Mux with audio
                cmd = [
                    self.ffmpeg_path,
                    "-i", clip_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    "-y",
                    output_path
                ]
            else:
                # Just copy
                cmd = [
                    self.ffmpeg_path,
                    "-i", clip_path,
                    "-c", "copy",
                    "-y",
                    output_path
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            return result.returncode == 0

        except Exception as e:
            Logger.error(f"Error in simple concat: {e}")
            return False

    def _simple_concat_multiple(
        self,
        clip_paths: List[str],
        output_path: str,
        audio_path: Optional[str] = None
    ) -> bool:
        """Simple concatenation without transitions using concat demuxer."""
        try:
            concat_file = self.temp_dir / "concat_list.txt"

            with open(concat_file, 'w') as f:
                for clip_path in clip_paths:
                    f.write(f"file '{os.path.abspath(clip_path)}'\n")

            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
            ]

            if audio_path:
                cmd.extend([
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest"
                ])
            else:
                cmd.extend(["-c", "copy"])

            cmd.extend(["-y", output_path])

            Logger.debug(f"Concatenating {len(clip_paths)} clips (no transitions)")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode != 0:
                Logger.error(f"Concatenation failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            Logger.error(f"Error in simple concat: {e}")
            return False

    def _xfade_concat(
        self,
        clip_paths: List[str],
        output_path: str,
        audio_path: Optional[str] = None,
        transition_duration: float = 0.5,
        transitions: Optional[List[str]] = None
    ) -> bool:
        """
        Concatenate clips with xfade transitions.

        Builds a complex filter graph for smooth transitions between clips.
        """
        try:
            num_clips = len(clip_paths)

            # Default to 'fade' if no transitions specified
            if transitions is None:
                transitions = ['fade'] * (num_clips - 1)

            # Ensure we have the right number of transitions
            if len(transitions) != num_clips - 1:
                Logger.warning(f"Expected {num_clips - 1} transitions, got {len(transitions)}. Using fade for missing.")
                transitions = transitions[:num_clips - 1]
                while len(transitions) < num_clips - 1:
                    transitions.append('fade')

            # Get duration of each clip
            Logger.debug("Getting clip durations...")
            clip_durations = []
            for clip_path in clip_paths:
                info = self.get_media_info(clip_path)
                duration = info.get('duration', 0)
                if duration == 0:
                    Logger.error(f"Could not get duration for {clip_path}")
                    return False
                clip_durations.append(duration)

            # Build xfade filter chain
            Logger.debug("Building xfade filter chain...")
            filter_parts = []
            current_offset = 0.0

            for i in range(num_clips - 1):
                transition = transitions[i]

                # Calculate offset for this transition
                # Offset is when the second clip starts overlapping
                if i == 0:
                    # First transition
                    offset = clip_durations[0] - transition_duration
                else:
                    # Subsequent transitions
                    offset = current_offset + clip_durations[i] - transition_duration

                current_offset = offset

                # Build xfade filter
                if i == 0:
                    # First transition: [0:v][1:v]xfade...
                    input_label = "[0:v][1:v]"
                    output_label = "[v01]" if num_clips > 2 else "[outv]"
                else:
                    # Subsequent: [vXY][Z:v]xfade...
                    prev_label = f"[v{i-1}{i}]"
                    input_label = f"{prev_label}[{i+1}:v]"
                    output_label = f"[v{i}{i+1}]" if i < num_clips - 2 else "[outv]"

                filter_parts.append(
                    f"{input_label}xfade=transition={transition}:"
                    f"duration={transition_duration}:offset={offset:.3f}{output_label}"
                )

            filter_complex = ";".join(filter_parts)

            Logger.debug(f"Filter complex: {filter_complex}")

            # Build FFmpeg command
            cmd = [self.ffmpeg_path]

            # Add all clip inputs
            for clip_path in clip_paths:
                cmd.extend(["-i", clip_path])

            # Add audio if provided
            if audio_path:
                cmd.extend(["-i", audio_path])

            # Add filter complex
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]"
            ])

            # Map audio
            if audio_path:
                cmd.extend([
                    "-map", f"{num_clips}:a",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest"
                ])

            # Video encoding settings
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-y",
                output_path
            ])

            Logger.info(f"Concatenating {num_clips} clips with {len(transitions)} transitions...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes for long videos
            )

            if result.returncode != 0:
                Logger.error(f"xfade concatenation failed: {result.stderr}")
                return False

            Logger.info("✓ Concatenation with transitions completed")
            return True

        except Exception as e:
            Logger.error(f"Error in xfade concat: {e}")
            Logger.exception("Full traceback:")
            return False

    def add_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_codec: str = "aac",
        audio_bitrate: str = "192k"
    ) -> bool:
        """
        Add audio track to video.

        Args:
            video_path: Input video file
            audio_path: Input audio file
            output_path: Output file
            audio_codec: Audio codec
            audio_bitrate: Audio bitrate

        Returns:
            True if successful
        """
        try:
            cmd = [
                self.ffmpeg_path,
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", audio_codec,
                "-b:a", audio_bitrate,
                "-shortest",
                "-y",
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            return result.returncode == 0

        except Exception as e:
            Logger.error(f"Error adding audio: {e}")
            return False

    def cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            import shutil
            if self.temp_dir.exists():
                for item in self.temp_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                Logger.debug("Temporary files cleaned up")
        except Exception as e:
            Logger.warning(f"Error cleaning up temp files: {e}")
