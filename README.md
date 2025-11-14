# mov3 🎬

**Full video automation engine designed to turn audio files into videos**

Automatically create short-form videos (YouTube Shorts, TikTok, Reels) from audio files and media assets. Fully offline, customizable, and power-user friendly.

## ✨ Features

- 🎵 **Audio-to-Video Automation** - Transform any audio file into a synchronized video
- 🎨 **Intelligent Media Selection** - Sequential or random media selection with anti-duplicate filtering
- ⏱️ **Smart Clip Planning** - Sophisticated duration planning with soft budgeting and error absorption
- 🎬 **FFmpeg Integration** - Hardware-accelerated encoding (NVENC, AMF, VideoToolbox)
- 🖼️ **Media Variations** - Automatic variations when reusing media (zoom, position, brightness)
- 🎞️ **Video Segment Reuse** - Smart reuse of different video segments to avoid repetition
- 📊 **Metrics & Telemetry** - Track processing statistics and performance
- 🖥️ **Dual Interface** - Both GUI (PyQt5) and CLI for different workflows
- ⚡ **Processing Modes** - Fast mode for bulk processing, Quality mode for premium output
- ⚙️ **Highly Configurable** - TOML-based configuration with per-job overrides

## 📋 Requirements

- **Python** 3.8 or higher
- **FFmpeg** (with hardware encoder support recommended)
- **System RAM**: 4GB minimum, 8GB+ recommended for HD videos

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/RanaAhmadGulabi/mov3.git
cd mov3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (if not already installed)
# Ubuntu/Debian:
sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/download.html
```

### 2. Prepare Your Content

Create your folder structure:

```
mov3/
├── examples/
│   ├── audio/
│   │   └── my_video.mp3       # Your audio file
│   └── media/
│       └── my_video/           # Folder matching audio filename
│           ├── 001.jpg
│           ├── 002.jpg
│           ├── 003.jpg
│           └── video.mp4
```

**Important:** The media folder name must match the audio filename (without extension).

### 3. Run It!

**CLI Mode:**
```bash
# Process a single file
python -m src.ui.cli --audio examples/audio/my_video.mp3

# Batch process all audio files
python -m src.ui.cli --batch

# With custom settings
python -m src.ui.cli --batch --mode fast --min-duration 3 --max-duration 7
```

**GUI Mode:**
```bash
# Coming soon!
python -m src.ui.gui
```

## 📖 Usage Guide

### Basic Usage

The simplest workflow:

1. Place your audio file in `examples/audio/`
2. Create a matching folder in `examples/media/` with images/videos
3. Run: `python -m src.ui.cli --batch`
4. Find your video in `output/`

### Command-Line Options

```bash
# Input options
--audio AUDIO         Process a single audio file
--batch              Batch process all audio files

# Directory options
--audio-dir DIR      Audio files directory
--media-dir DIR      Media folders directory
--output-dir DIR     Output directory

# Processing options
--mode {fast,quality}        Processing mode
--min-duration SECONDS       Minimum clip duration (default: 2.0)
--max-duration SECONDS       Maximum clip duration (default: 5.0)
--resolution WIDTHxHEIGHT   Output resolution (e.g., 1920x1080)
--fps FPS                    Frames per second (default: 30)
--codec CODEC               Video codec (libx264, h264_nvenc, h264_amf)
--selection-mode {sequential,random}  Media selection mode

# Other options
--no-prompt          Don't prompt for confirmation
--log-level LEVEL    Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Examples

**1. Process with custom resolution:**
```bash
python -m src.ui.cli --audio my_video.mp3 --resolution 1080x1920 --fps 60
```

**2. Fast batch processing with hardware encoding:**
```bash
python -m src.ui.cli --batch --mode fast --codec h264_nvenc
```

**3. Quality mode with longer clips:**
```bash
python -m src.ui.cli --audio my_video.mp3 --mode quality --min-duration 3 --max-duration 8
```

**4. Random media selection:**
```bash
python -m src.ui.cli --batch --selection-mode random
```

## ⚙️ Configuration

Configuration files are located in the `config/` directory:

### `config/settings.toml`

Main settings file for video, audio, processing, and validation options.

```toml
[video]
default_resolution = [1920, 1080]
default_fps = 30
default_codec = "libx264"
hw_encoders = ["h264_nvenc", "h264_amf"]

[processing.quality]
min_clip_duration = 2.0
max_clip_duration = 5.0
transitions_enabled = true
effects_full = true
```

### `config/effects.toml`

Effects and transitions configuration.

```toml
[kenburns]
enabled = true
zoom_min = 0.95
zoom_max = 1.10

[variations]
enabled = true
zoom_range = [0.95, 1.15]
```

### `config/captions.toml`

Caption styling presets (coming soon).

## 🎯 Processing Modes

### Fast Mode
- Optimized for speed
- Longer clip durations (less encoding)
- Minimal transitions
- Perfect for bulk processing

### Quality Mode
- Optimized for output quality
- Shorter clips with more variety
- Full effects and transitions
- Better pacing and visual appeal

## 🔧 How It Works

1. **Validation** - Check audio and media files exist
2. **Planning** - Calculate optimal clip durations to match audio length
3. **Selection** - Choose media files (sequential or random)
4. **Encoding** - Encode each clip with FFmpeg
5. **Concatenation** - Merge clips and sync audio
6. **Finalization** - Output final video

### Intelligent Duration Planning

The engine uses a sophisticated algorithm to match video length to audio:

- Distributes duration across clips within min/max constraints
- Applies soft budgeting (±25% smoothing between adjacent clips)
- Absorbs timing errors across all clips
- Extends/trims final clip if needed for perfect sync

### Media Reuse Strategy

When you have limited media:

- **Images**: Reused with variations (zoom, position, brightness, flip)
- **Videos**: Different time segments used to avoid repetition
- Warnings shown before processing if media is insufficient

## 📊 Output

Each job produces:

- `{audio_name}_final.mp4` - Final video in output directory
- Processing logs in `logs/` directory
- Metrics (if enabled) in JSON format

## 🐛 Troubleshooting

### "FFmpeg not found"
Install FFmpeg and ensure it's in your PATH:
```bash
# Check if FFmpeg is installed
ffmpeg -version
```

### "Media folder not found"
Ensure your media folder name exactly matches the audio filename:
```
audio/my_video.mp3 → media/my_video/
```

### "Not enough media files"
The tool will warn you and ask for confirmation. Options:
- Add more media files
- Continue anyway (media will be reused with variations)
- Cancel the job

### Hardware encoder not working
Check available encoders:
```bash
ffmpeg -encoders | grep h264
```

If hardware encoders aren't available, the tool will automatically fallback to software encoding (libx264).

## 🚧 Coming Soon

- [ ] PyQt5 GUI application
- [ ] Transitions and effects (Ken Burns, color filters, glitch, etc.)
- [ ] Caption generation with Whisper AI
- [ ] Word-level karaoke captions
- [ ] Effect profiles and presets
- [ ] Batch queue management
- [ ] Real-time preview
- [ ] Web-based UI option

## 📝 Project Structure

```
mov3/
├── src/
│   ├── core/           # Core engine and planning
│   ├── media/          # Media selection
│   ├── ffmpeg/         # FFmpeg orchestration
│   ├── effects/        # Effects and transitions
│   ├── captions/       # Caption generation
│   ├── ui/             # GUI and CLI interfaces
│   ├── utils/          # Utilities and logging
│   └── config/         # Configuration loader
├── config/             # Configuration files
├── examples/           # Example audio and media
├── tests/              # Test suite
├── docs/               # Documentation
└── output/             # Generated videos
```

## 🤝 Contributing

Contributions are welcome! Please check the [CLAUDE.md](CLAUDE.md) file for development guidelines.

## 📄 License

[MIT License](LICENSE) (or specify your chosen license)

## 🙏 Acknowledgments

- Built with FFmpeg, MoviePy, and PyQt5
- Inspired by CapCut automation and short-form video tools

---

**Made with ❤️ for content creators**

For questions, issues, or feature requests, please open an issue on GitHub.
