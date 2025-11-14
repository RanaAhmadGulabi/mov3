"""
Configuration loader for mov3 video automation engine.
Handles loading and merging TOML configuration files.
"""

import os
import toml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    """Main configuration container."""

    # General settings
    project_name: str = "mov3"
    version: str = "0.1.0"
    log_level: str = "INFO"

    # Paths
    audio_dir: str = "examples/audio"
    media_dir: str = "examples/media"
    output_dir: str = "output"
    logs_dir: str = "logs"
    temp_dir: str = "temp"

    # Video settings
    resolution: tuple = (1920, 1080)
    fps: int = 30
    codec: str = "libx264"
    preset: str = "medium"
    crf: int = 23

    # Audio settings
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    sample_rate: int = 44100

    # Processing mode
    mode: str = "quality"  # fast or quality
    max_workers: int = 4

    # Clip settings
    min_clip_duration: float = 2.0
    max_clip_duration: float = 5.0
    overlap_duration: float = 0.5
    soft_budget_tolerance: float = 0.25

    # Media selection
    selection_mode: str = "sequential"  # sequential or random
    anti_consecutive: bool = True

    # Validation
    warn_insufficient_media: bool = True
    prompt_on_shortage: bool = True
    min_media_files: int = 3

    # Hardware encoding
    hw_encoders: list = field(default_factory=lambda: ["h264_nvenc", "h264_amf"])
    hw_fallback: str = "libx264"

    # Captions
    captions_enabled: bool = False
    caption_type: str = "closed"
    caption_language: str = "en"
    whisper_model: str = "base"

    # Metrics
    metrics_enabled: bool = True

    # Effects
    effects: Dict[str, Any] = field(default_factory=dict)

    # Full raw config
    raw: Dict[str, Any] = field(default_factory=dict)


class ConfigLoader:
    """Loads and manages configuration files."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration loader.

        Args:
            config_dir: Path to configuration directory. Defaults to 'config'.
        """
        if config_dir is None:
            # Get config directory relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "config"

        self.config_dir = Path(config_dir)
        self._settings = None
        self._effects = None
        self._captions = None

    def load_settings(self) -> Dict[str, Any]:
        """Load main settings configuration."""
        if self._settings is None:
            settings_file = self.config_dir / "settings.toml"
            if settings_file.exists():
                self._settings = toml.load(settings_file)
            else:
                self._settings = {}
        return self._settings

    def load_effects(self) -> Dict[str, Any]:
        """Load effects configuration."""
        if self._effects is None:
            effects_file = self.config_dir / "effects.toml"
            if effects_file.exists():
                self._effects = toml.load(effects_file)
            else:
                self._effects = {}
        return self._effects

    def load_captions(self) -> Dict[str, Any]:
        """Load caption styling configuration."""
        if self._captions is None:
            captions_file = self.config_dir / "captions.toml"
            if captions_file.exists():
                self._captions = toml.load(captions_file)
            else:
                self._captions = {}
        return self._captions

    def get_config(self, overrides: Optional[Dict[str, Any]] = None) -> Config:
        """
        Get merged configuration with optional overrides.

        Args:
            overrides: Dictionary of values to override defaults

        Returns:
            Config object with merged settings
        """
        settings = self.load_settings()
        effects = self.load_effects()

        # Extract values from nested settings
        general = settings.get("general", {})
        paths = settings.get("paths", {})
        video = settings.get("video", {})
        audio = settings.get("audio", {})
        processing = settings.get("processing", {})
        clips = settings.get("clips", {})
        media = settings.get("media", {})
        validation = settings.get("validation", {})
        captions = settings.get("captions", {})
        metrics = settings.get("metrics", {})

        # Build config object
        config = Config(
            project_name=general.get("project_name", "mov3"),
            version=general.get("version", "0.1.0"),
            log_level=general.get("log_level", "INFO"),

            audio_dir=paths.get("audio_dir", "examples/audio"),
            media_dir=paths.get("media_dir", "examples/media"),
            output_dir=paths.get("output_dir", "output"),
            logs_dir=paths.get("logs_dir", "logs"),
            temp_dir=paths.get("temp_dir", "temp"),

            resolution=tuple(video.get("default_resolution", [1920, 1080])),
            fps=video.get("default_fps", 30),
            codec=video.get("default_codec", "libx264"),
            preset=video.get("default_preset", "medium"),
            crf=video.get("default_crf", 23),

            audio_codec=audio.get("default_codec", "aac"),
            audio_bitrate=audio.get("default_bitrate", "192k"),
            sample_rate=audio.get("sample_rate", 44100),

            mode=processing.get("mode", "quality"),
            max_workers=processing.get("max_workers", 4),

            min_clip_duration=clips.get("min_duration", 2.0),
            max_clip_duration=clips.get("max_duration", 5.0),
            overlap_duration=clips.get("overlap_duration", 0.5),
            soft_budget_tolerance=clips.get("soft_budget_tolerance", 0.25),

            selection_mode=clips.get("selection_mode", "sequential"),
            anti_consecutive=clips.get("anti_consecutive", True),

            warn_insufficient_media=validation.get("warn_insufficient_media", True),
            prompt_on_shortage=validation.get("prompt_on_shortage", True),
            min_media_files=validation.get("min_media_files", 3),

            hw_encoders=video.get("hw_encoders", ["h264_nvenc", "h264_amf"]),
            hw_fallback=video.get("hw_fallback", "libx264"),

            captions_enabled=captions.get("enabled", False),
            caption_type=captions.get("type", "closed"),
            caption_language=captions.get("language", "en"),
            whisper_model=captions.get("whisper_model", "base"),

            metrics_enabled=metrics.get("enabled", True),

            effects=effects,
            raw=settings
        )

        # Apply overrides if provided
        if overrides:
            for key, value in overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        return config

    def get_caption_style(self, style_name: str = "default") -> Dict[str, Any]:
        """
        Get caption style configuration.

        Args:
            style_name: Name of the style preset

        Returns:
            Dictionary with style settings
        """
        captions = self.load_captions()
        return captions.get(style_name, captions.get("default", {}))


# Global config loader instance
_loader = None


def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """Get or create the global config loader instance."""
    global _loader
    if _loader is None:
        _loader = ConfigLoader(config_dir)
    return _loader


def load_config(overrides: Optional[Dict[str, Any]] = None) -> Config:
    """Convenience function to load configuration."""
    loader = get_config_loader()
    return loader.get_config(overrides)
