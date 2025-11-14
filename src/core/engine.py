"""
Core processing engine for mov3 video automation.
Orchestrates the entire pipeline from audio to final video.
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from ..config.loader import Config
from ..media.selector import MediaSelector, SelectionMode, MediaType
from ..core.planner import DurationPlanner, ClipPlan
from ..ffmpeg.orchestrator import FFmpegOrchestrator
from ..utils.logger import Logger


class JobStatus(Enum):
    """Status of a processing job."""
    PENDING = "pending"
    VALIDATING = "validating"
    PLANNING = "planning"
    PROCESSING = "processing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """Result of a processing job."""
    audio_file: str
    output_file: str
    status: JobStatus
    duration: float = 0.0
    clips_processed: int = 0
    error_message: str = ""
    warnings: List[str] = None
    metrics: Dict = None
    start_time: float = 0.0
    end_time: float = 0.0

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metrics is None:
            self.metrics = {}

    @property
    def processing_time(self) -> float:
        """Total processing time in seconds."""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        data['processing_time'] = self.processing_time
        return data


class VideoEngine:
    """
    Main video automation engine.

    Coordinates:
    - Media selection
    - Clip duration planning
    - FFmpeg encoding
    - Effect application
    - Audio syncing
    - Final output
    """

    def __init__(
        self,
        config: Config,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        Initialize the video engine.

        Args:
            config: Configuration object
            progress_callback: Optional callback for progress updates (message, percentage)
        """
        self.config = config
        self.progress_callback = progress_callback

        # Create necessary directories
        self._setup_directories()

        # Initialize components
        self.ffmpeg = FFmpegOrchestrator(temp_dir=self.config.temp_dir)

        Logger.info("VideoEngine initialized")

    def _setup_directories(self):
        """Create necessary directories."""
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.temp_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.logs_dir).mkdir(parents=True, exist_ok=True)

    def _report_progress(self, message: str, percentage: float = 0.0):
        """Report progress to callback if available."""
        Logger.info(f"Progress: {message} ({percentage:.1f}%)")
        if self.progress_callback:
            self.progress_callback(message, percentage)

    def process_audio_file(
        self,
        audio_path: str,
        overrides: Optional[Dict] = None,
        user_confirm_callback: Optional[Callable[[str], bool]] = None
    ) -> JobResult:
        """
        Process a single audio file into a video.

        Args:
            audio_path: Path to audio file
            overrides: Optional config overrides for this job
            user_confirm_callback: Callback to ask user for confirmation (returns True/False)

        Returns:
            JobResult with outcome
        """
        audio_path = Path(audio_path)
        audio_name = audio_path.stem

        result = JobResult(
            audio_file=str(audio_path),
            output_file="",
            status=JobStatus.PENDING,
            start_time=time.time()
        )

        try:
            Logger.info(f"="*60)
            Logger.info(f"Processing: {audio_name}")
            Logger.info(f"="*60)

            # Merge config with overrides
            job_config = self._merge_config(overrides)

            # 1. VALIDATION PHASE
            result.status = JobStatus.VALIDATING
            self._report_progress("Validating inputs...", 5)

            validation_result = self._validate_inputs(audio_path, audio_name, job_config)

            if not validation_result['valid']:
                if validation_result.get('prompt_user', False) and user_confirm_callback:
                    # Ask user if they want to continue
                    message = validation_result['message']
                    if not user_confirm_callback(message):
                        result.status = JobStatus.CANCELLED
                        result.error_message = "User cancelled due to validation warning"
                        return result
                    else:
                        result.warnings.append(validation_result['message'])
                else:
                    result.status = JobStatus.FAILED
                    result.error_message = validation_result['message']
                    result.end_time = time.time()
                    return result

            # Add any warnings
            if 'warnings' in validation_result:
                result.warnings.extend(validation_result['warnings'])

            # 2. Get audio duration
            audio_info = self.ffmpeg.get_media_info(str(audio_path))
            audio_duration = audio_info.get('duration', 0)

            if audio_duration == 0:
                result.status = JobStatus.FAILED
                result.error_message = "Could not determine audio duration"
                result.end_time = time.time()
                return result

            result.duration = audio_duration
            Logger.info(f"Audio duration: {audio_duration:.2f}s")

            # 3. PLANNING PHASE
            result.status = JobStatus.PLANNING
            self._report_progress("Planning clips...", 15)

            # Initialize media selector
            media_selector = MediaSelector(
                media_dir=Path(job_config.media_dir),
                audio_name=audio_name,
                mode=SelectionMode.SEQUENTIAL if job_config.selection_mode == "sequential" else SelectionMode.RANDOM,
                anti_consecutive=job_config.anti_consecutive
            )

            # Plan clip durations
            planner = DurationPlanner(
                audio_duration=audio_duration,
                min_clip_duration=job_config.min_clip_duration,
                max_clip_duration=job_config.max_clip_duration,
                overlap_duration=job_config.overlap_duration,
                soft_budget_tolerance=job_config.soft_budget_tolerance
            )

            clip_plans = planner.plan_clips()
            result.clips_processed = len(clip_plans)

            Logger.info(f"Planned {len(clip_plans)} clips")
            summary = planner.get_summary(clip_plans)
            Logger.info(f"Plan summary: {summary}")

            # 4. PROCESSING PHASE
            result.status = JobStatus.PROCESSING
            self._report_progress("Encoding clips...", 25)

            # Process each clip
            clip_files = []
            for i, clip_plan in enumerate(clip_plans):
                progress = 25 + (i / len(clip_plans)) * 60  # 25% to 85%
                self._report_progress(f"Processing clip {i+1}/{len(clip_plans)}", progress)

                clip_file = self._process_clip(
                    media_selector,
                    clip_plan,
                    i,
                    job_config
                )

                if clip_file:
                    clip_files.append(clip_file)
                else:
                    Logger.warning(f"Failed to process clip {i}")

            if not clip_files:
                result.status = JobStatus.FAILED
                result.error_message = "No clips were successfully processed"
                result.end_time = time.time()
                return result

            # 5. FINALIZATION PHASE
            result.status = JobStatus.FINALIZING
            self._report_progress("Finalizing video...", 90)

            # Concatenate clips
            output_file = Path(job_config.output_dir) / f"{audio_name}_final.mp4"
            result.output_file = str(output_file)

            success = self.ffmpeg.concatenate_clips(
                clip_paths=clip_files,
                output_path=str(output_file),
                audio_path=str(audio_path),
                transition_duration=0.0  # TODO: Add transition support
            )

            if not success:
                result.status = JobStatus.FAILED
                result.error_message = "Failed to concatenate clips"
                result.end_time = time.time()
                return result

            # Clean up temp files
            self.ffmpeg.cleanup_temp_files()

            # Success!
            result.status = JobStatus.COMPLETED
            result.end_time = time.time()
            self._report_progress("Complete!", 100)

            Logger.info(f"✓ Video created: {output_file}")
            Logger.info(f"✓ Processing time: {result.processing_time:.2f}s")

            # Collect metrics
            result.metrics = {
                'audio_duration': audio_duration,
                'clips_count': len(clip_plans),
                'media_stats': media_selector.get_statistics(),
                'plan_summary': summary
            }

            return result

        except Exception as e:
            Logger.exception(f"Error processing {audio_name}")
            result.status = JobStatus.FAILED
            result.error_message = str(e)
            result.end_time = time.time()
            return result

    def _merge_config(self, overrides: Optional[Dict]) -> Config:
        """Merge config with overrides."""
        if not overrides:
            return self.config

        # Create a copy of config and apply overrides
        from copy import deepcopy
        merged = deepcopy(self.config)

        for key, value in overrides.items():
            if hasattr(merged, key):
                setattr(merged, key, value)

        return merged

    def _validate_inputs(
        self,
        audio_path: Path,
        audio_name: str,
        config: Config
    ) -> Dict:
        """
        Validate inputs before processing.

        Returns:
            Dictionary with 'valid', 'message', 'prompt_user', 'warnings'
        """
        result = {
            'valid': True,
            'message': '',
            'prompt_user': False,
            'warnings': []
        }

        # Check audio file exists
        if not audio_path.exists():
            result['valid'] = False
            result['message'] = f"Audio file not found: {audio_path}"
            return result

        # Check media folder exists
        media_folder = Path(config.media_dir) / audio_name
        if not media_folder.exists():
            result['valid'] = False
            result['message'] = f"Media folder not found: {media_folder}"
            return result

        # Check media count
        media_files = list(media_folder.glob("*"))
        media_count = len([f for f in media_files if f.is_file()])

        if media_count == 0:
            result['valid'] = False
            result['message'] = f"No media files found in: {media_folder}"
            return result

        # Warn if insufficient media
        if config.warn_insufficient_media and media_count < config.min_media_files:
            warning_msg = (
                f"Warning: Only {media_count} media file(s) found. "
                f"Recommended minimum: {config.min_media_files}. "
                f"Media will be reused with variations."
            )
            result['warnings'].append(warning_msg)

            if config.prompt_on_shortage:
                result['valid'] = False
                result['prompt_user'] = True
                result['message'] = warning_msg + "\n\nDo you want to continue?"

        return result

    def _process_clip(
        self,
        media_selector: MediaSelector,
        clip_plan: ClipPlan,
        clip_index: int,
        config: Config
    ) -> Optional[str]:
        """
        Process a single clip.

        Args:
            media_selector: Media selector instance
            clip_plan: Plan for this clip
            clip_index: Index of this clip
            config: Job configuration

        Returns:
            Path to encoded clip file, or None if failed
        """
        try:
            # Select media
            selection = media_selector.select_next(
                duration=clip_plan.duration,
                avoid_file=media_selector.last_selected if config.anti_consecutive else None
            )

            # Generate temp file path
            temp_file = Path(config.temp_dir) / f"clip_{clip_index:04d}.mp4"

            # Encode based on media type
            if selection.file.type == MediaType.IMAGE:
                success = self.ffmpeg.encode_image_clip(
                    image_path=str(selection.file.path),
                    output_path=str(temp_file),
                    duration=selection.duration,
                    resolution=config.resolution,
                    fps=config.fps,
                    codec=config.codec,
                    preset=config.preset,
                    crf=config.crf
                )
            else:  # VIDEO
                success = self.ffmpeg.encode_video_clip(
                    video_path=str(selection.file.path),
                    output_path=str(temp_file),
                    start_time=selection.start_time or 0,
                    duration=selection.duration,
                    resolution=config.resolution,
                    fps=config.fps,
                    codec=config.codec,
                    preset=config.preset,
                    crf=config.crf
                )

            if success:
                return str(temp_file)
            else:
                Logger.error(f"Failed to encode clip {clip_index}")
                return None

        except Exception as e:
            Logger.error(f"Error processing clip {clip_index}: {e}")
            return None

    def batch_process(
        self,
        audio_dir: Optional[str] = None,
        overrides: Optional[Dict] = None,
        user_confirm_callback: Optional[Callable[[str], bool]] = None
    ) -> List[JobResult]:
        """
        Batch process all audio files in a directory.

        Args:
            audio_dir: Directory containing audio files (default: config.audio_dir)
            overrides: Optional config overrides
            user_confirm_callback: Callback for user confirmation

        Returns:
            List of JobResult objects
        """
        audio_dir = Path(audio_dir or self.config.audio_dir)

        if not audio_dir.exists():
            Logger.error(f"Audio directory not found: {audio_dir}")
            return []

        # Find all audio files
        audio_files = []
        for ext in self.config.raw.get('media', {}).get('audio_formats', ['.mp3', '.wav']):
            audio_files.extend(audio_dir.glob(f"*{ext}"))

        if not audio_files:
            Logger.warning(f"No audio files found in {audio_dir}")
            return []

        Logger.info(f"Found {len(audio_files)} audio file(s) to process")

        results = []
        for i, audio_file in enumerate(audio_files):
            Logger.info(f"\n[{i+1}/{len(audio_files)}] Processing: {audio_file.name}")

            result = self.process_audio_file(
                audio_path=str(audio_file),
                overrides=overrides,
                user_confirm_callback=user_confirm_callback
            )

            results.append(result)

            # Log result
            if result.status == JobStatus.COMPLETED:
                Logger.info(f"✓ Success: {result.output_file}")
            elif result.status == JobStatus.CANCELLED:
                Logger.warning(f"⊗ Cancelled: {audio_file.name}")
            else:
                Logger.error(f"✗ Failed: {result.error_message}")

        # Summary
        Logger.info("\n" + "="*60)
        Logger.info("BATCH PROCESSING SUMMARY")
        Logger.info("="*60)

        completed = sum(1 for r in results if r.status == JobStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == JobStatus.FAILED)
        cancelled = sum(1 for r in results if r.status == JobStatus.CANCELLED)

        Logger.info(f"Total: {len(results)}")
        Logger.info(f"✓ Completed: {completed}")
        Logger.info(f"✗ Failed: {failed}")
        Logger.info(f"⊗ Cancelled: {cancelled}")

        total_time = sum(r.processing_time for r in results)
        Logger.info(f"Total processing time: {total_time:.2f}s")

        return results
