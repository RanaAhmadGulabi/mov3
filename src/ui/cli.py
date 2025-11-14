"""
Command-line interface for mov3 video automation engine.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.loader import load_config
from src.core.engine import VideoEngine, JobStatus
from src.utils.logger import Logger, setup_logger


def user_confirm(message: str) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: Message to display

    Returns:
        True if user confirms, False otherwise
    """
    print(f"\n{message}")
    response = input("Continue? (y/n): ").strip().lower()
    return response in ['y', 'yes']


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="mov3 - Video Automation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single audio file
  python -m src.ui.cli --audio my_audio.mp3

  # Batch process all audio files in a directory
  python -m src.ui.cli --batch

  # Use custom settings
  python -m src.ui.cli --batch --mode fast --min-duration 3 --max-duration 7

  # Specify custom directories
  python -m src.ui.cli --audio-dir ./my_audio --media-dir ./my_media --output-dir ./output
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument(
        '--audio',
        type=str,
        help='Process a single audio file'
    )
    input_group.add_argument(
        '--batch',
        action='store_true',
        help='Batch process all audio files in audio directory'
    )

    # Directory options
    parser.add_argument(
        '--audio-dir',
        type=str,
        help='Directory containing audio files (default: examples/audio)'
    )
    parser.add_argument(
        '--media-dir',
        type=str,
        help='Directory containing media subfolders (default: examples/media)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Output directory for videos (default: output)'
    )

    # Processing options
    parser.add_argument(
        '--mode',
        type=str,
        choices=['fast', 'quality'],
        help='Processing mode (fast or quality)'
    )
    parser.add_argument(
        '--min-duration',
        type=float,
        help='Minimum clip duration in seconds'
    )
    parser.add_argument(
        '--max-duration',
        type=float,
        help='Maximum clip duration in seconds'
    )
    parser.add_argument(
        '--resolution',
        type=str,
        help='Output resolution (e.g., 1920x1080, 1080x1920)'
    )
    parser.add_argument(
        '--fps',
        type=int,
        help='Output frames per second'
    )
    parser.add_argument(
        '--codec',
        type=str,
        help='Video codec (libx264, h264_nvenc, h264_amf)'
    )
    parser.add_argument(
        '--selection-mode',
        type=str,
        choices=['sequential', 'random'],
        help='Media selection mode'
    )

    # Other options
    parser.add_argument(
        '--no-prompt',
        action='store_true',
        help='Do not prompt for confirmation on warnings (auto-continue)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logger(log_level=args.log_level)

    Logger.info("mov3 Video Automation Engine")
    Logger.info("=" * 60)

    # Load configuration
    try:
        config = load_config()

        # Apply command-line overrides
        overrides = {}

        if args.audio_dir:
            overrides['audio_dir'] = args.audio_dir
        if args.media_dir:
            overrides['media_dir'] = args.media_dir
        if args.output_dir:
            overrides['output_dir'] = args.output_dir
        if args.mode:
            overrides['mode'] = args.mode
        if args.min_duration:
            overrides['min_clip_duration'] = args.min_duration
        if args.max_duration:
            overrides['max_clip_duration'] = args.max_duration
        if args.resolution:
            width, height = args.resolution.split('x')
            overrides['resolution'] = (int(width), int(height))
        if args.fps:
            overrides['fps'] = args.fps
        if args.codec:
            overrides['codec'] = args.codec
        if args.selection_mode:
            overrides['selection_mode'] = args.selection_mode
        if args.no_prompt:
            overrides['prompt_on_shortage'] = False

        # Reload config with overrides
        config = load_config(overrides=overrides)

        Logger.info(f"Audio directory: {config.audio_dir}")
        Logger.info(f"Media directory: {config.media_dir}")
        Logger.info(f"Output directory: {config.output_dir}")
        Logger.info(f"Mode: {config.mode}")
        Logger.info(f"Resolution: {config.resolution[0]}x{config.resolution[1]}")
        Logger.info("")

    except Exception as e:
        Logger.error(f"Failed to load configuration: {e}")
        return 1

    # Initialize engine
    try:
        engine = VideoEngine(config)
    except Exception as e:
        Logger.error(f"Failed to initialize engine: {e}")
        return 1

    # Process
    try:
        confirm_callback = None if args.no_prompt else user_confirm

        if args.audio:
            # Process single file
            Logger.info(f"Processing single file: {args.audio}")
            result = engine.process_audio_file(
                audio_path=args.audio,
                user_confirm_callback=confirm_callback
            )

            if result.status == JobStatus.COMPLETED:
                Logger.info("\n✓ Success!")
                Logger.info(f"Output: {result.output_file}")
                Logger.info(f"Duration: {result.duration:.2f}s")
                Logger.info(f"Clips: {result.clips_processed}")
                Logger.info(f"Processing time: {result.processing_time:.2f}s")
                return 0
            elif result.status == JobStatus.CANCELLED:
                Logger.warning("\n⊗ Cancelled by user")
                return 2
            else:
                Logger.error(f"\n✗ Failed: {result.error_message}")
                return 1

        else:
            # Batch process (default if no --audio specified)
            Logger.info("Batch processing mode")
            results = engine.batch_process(
                user_confirm_callback=confirm_callback
            )

            if not results:
                Logger.warning("No files were processed")
                return 1

            # Check if any succeeded
            successful = [r for r in results if r.status == JobStatus.COMPLETED]
            if successful:
                Logger.info(f"\n✓ Successfully processed {len(successful)} file(s)")
                return 0
            else:
                Logger.error("\n✗ No files were successfully processed")
                return 1

    except KeyboardInterrupt:
        Logger.warning("\n⊗ Interrupted by user")
        return 130
    except Exception as e:
        Logger.exception("Unexpected error during processing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
