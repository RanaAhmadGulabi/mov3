# CLAUDE.md - AI Assistant Guide for mov3

## Project Overview

**mov3** is a full video automation engine designed to turn audio files into videos. This project aims to automate the entire pipeline from audio input to rendered video output with visual elements, captions, and effects.

### Project Status
- **Stage**: Early development / Initial setup
- **Primary Language**: TBD (likely Python or JavaScript/TypeScript)
- **License**: Not yet specified

## Repository Structure

```
mov3/
├── README.md           # Project description
├── CLAUDE.md          # This file - AI assistant guide
└── .git/              # Git repository
```

### Expected Future Structure

As the project develops, expect the following structure:

```
mov3/
├── src/               # Source code
│   ├── audio/         # Audio processing modules
│   ├── video/         # Video generation and rendering
│   ├── effects/       # Visual effects and transitions
│   ├── captions/      # Subtitle/caption generation
│   └── pipeline/      # Automation pipeline orchestration
├── tests/             # Test suite
├── docs/              # Documentation
├── examples/          # Example usage and demos
├── config/            # Configuration files
├── scripts/           # Build and utility scripts
├── assets/            # Static assets (fonts, templates, etc.)
└── output/            # Generated videos (gitignored)
```

## Technology Stack Considerations

### Core Technologies (To Be Decided)
When implementing this project, consider:

**Backend Options:**
- **Python**: Best for audio/video processing (ffmpeg-python, moviepy, pydub)
- **Node.js/TypeScript**: Good for pipeline orchestration and API services
- **Rust**: For performance-critical components

**Key Libraries to Consider:**
- **Audio Processing**: ffmpeg, pydub, librosa, whisper (for transcription)
- **Video Rendering**: moviepy, ffmpeg, opencv-python
- **AI/ML**: OpenAI Whisper, Stable Diffusion, DALL-E (for visuals)
- **Text Processing**: spaCy, NLTK (for caption analysis)

## Development Workflow

### Starting New Features

1. **Create feature branch** from main:
   ```bash
   git checkout -b feature/feature-name
   ```

2. **Plan your work** using TodoWrite tool to track tasks

3. **Implement incrementally**:
   - Write tests first (TDD approach recommended)
   - Implement functionality
   - Document as you go

4. **Commit frequently** with clear messages:
   ```bash
   git commit -m "feat: add audio input processing"
   ```

### Commit Message Conventions

Follow Conventional Commits specification:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Build/tooling changes
- `style:` - Code style changes (formatting)

### Code Quality Standards

1. **Testing**:
   - Aim for 80%+ code coverage
   - Write unit tests for all core functions
   - Include integration tests for pipeline components
   - Add end-to-end tests for complete workflows

2. **Documentation**:
   - All public functions must have docstrings
   - Update README.md when adding major features
   - Maintain API documentation
   - Include usage examples

3. **Code Style**:
   - Use consistent formatting (Black for Python, Prettier for JS/TS)
   - Follow language-specific style guides (PEP 8, Airbnb, etc.)
   - Use meaningful variable names
   - Keep functions small and focused

## AI Assistant Best Practices

### When Working on This Project

1. **Always Check Dependencies**:
   - Verify required audio/video codecs are available
   - Check for ffmpeg installation
   - Confirm API keys for AI services (if needed)

2. **Performance Considerations**:
   - Video processing is resource-intensive
   - Implement progress tracking for long operations
   - Consider async/parallel processing where possible
   - Add caching for expensive operations

3. **Error Handling**:
   - Validate input audio files (format, length, quality)
   - Handle missing dependencies gracefully
   - Provide clear error messages with troubleshooting steps
   - Log errors appropriately

4. **Security**:
   - Never commit API keys or credentials
   - Sanitize file paths to prevent directory traversal
   - Validate user inputs
   - Be cautious with subprocess execution

5. **File Management**:
   - Clean up temporary files after processing
   - Don't commit generated videos to git
   - Use .gitignore for output directories
   - Implement proper resource cleanup

### Common Tasks

#### Adding New Audio Processing Feature
1. Create module in `src/audio/`
2. Write tests in `tests/audio/`
3. Document the audio format requirements
4. Update pipeline to integrate new feature

#### Adding Visual Effects
1. Create effect in `src/effects/`
2. Define effect parameters and defaults
3. Add preview capability if possible
4. Test with various video resolutions

#### Extending the Pipeline
1. Identify the pipeline stage (pre/mid/post processing)
2. Implement as a modular component
3. Add configuration options
4. Ensure it's composable with other stages

## Configuration Management

### Expected Configuration Files

- **config.yaml/json**: Main configuration
  - Default video settings (resolution, fps, codec)
  - Audio processing parameters
  - Effect templates
  - Output preferences

- **.env**: Environment variables (never commit)
  - API keys
  - Service endpoints
  - Secret tokens

- **pyproject.toml** or **package.json**: Dependencies
  - Keep dependencies minimal
  - Lock versions for stability
  - Document why each dependency is needed

## Testing Strategy

### Test Categories

1. **Unit Tests**:
   - Individual function testing
   - Mock external dependencies
   - Fast execution

2. **Integration Tests**:
   - Test component interactions
   - Use sample audio/video files
   - Verify pipeline stages work together

3. **End-to-End Tests**:
   - Full pipeline execution
   - Real audio file → video output
   - May be slower, run less frequently

4. **Performance Tests**:
   - Benchmark critical operations
   - Monitor memory usage
   - Test with various file sizes

### Test Data
- Keep test audio files small (< 1MB)
- Use various formats (MP3, WAV, FLAC)
- Include edge cases (silence, noise, multiple speakers)

## Dependencies and Environment

### System Requirements
Document in README.md:
- Operating system compatibility
- Required system libraries (ffmpeg, etc.)
- Minimum hardware specs (RAM, storage)

### Python Virtual Environment (if Python)
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Node.js (if Node/TypeScript)
```bash
npm install
# or
yarn install
```

## Common Pitfalls to Avoid

1. **Memory Leaks**: Always close file handles and clean up resources
2. **Blocking Operations**: Use async for I/O operations
3. **Hardcoded Paths**: Use path joining utilities
4. **Assuming File Formats**: Always validate and convert if needed
5. **Not Handling Large Files**: Implement streaming where possible
6. **Missing Progress Indicators**: Long operations need progress feedback
7. **Poor Error Messages**: Include context and suggested fixes

## Development Priorities

### Phase 1: Foundation (Current)
- [ ] Choose technology stack
- [ ] Set up project structure
- [ ] Configure development environment
- [ ] Implement basic audio input handling
- [ ] Set up testing framework

### Phase 2: Core Features
- [ ] Audio transcription
- [ ] Caption generation
- [ ] Basic video rendering
- [ ] Simple visual templates

### Phase 3: Enhancement
- [ ] Advanced effects
- [ ] Multiple output formats
- [ ] Batch processing
- [ ] API/CLI interface

### Phase 4: Polish
- [ ] Performance optimization
- [ ] Comprehensive documentation
- [ ] Example gallery
- [ ] User guides

## Git Workflow

### Branch Strategy
- **main**: Production-ready code
- **develop**: Integration branch (if using)
- **feature/**: New features
- **fix/**: Bug fixes
- **docs/**: Documentation updates

### Before Committing
1. Run tests: `pytest` or `npm test`
2. Check formatting: `black .` or `prettier --write .`
3. Verify no secrets in code
4. Update relevant documentation

### Pull Request Checklist
- [ ] Tests pass
- [ ] Code is formatted
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Descriptive PR title and description
- [ ] Linked to relevant issues

## Resources and References

### Audio/Video Processing
- [ffmpeg Documentation](https://ffmpeg.org/documentation.html)
- [MoviePy User Guide](https://zulko.github.io/moviepy/)
- [PyDub Documentation](https://github.com/jiaaro/pydub)

### AI/ML for Audio
- [OpenAI Whisper](https://github.com/openai/whisper)
- [AssemblyAI](https://www.assemblyai.com/)

### Video Rendering
- [OpenCV](https://opencv.org/)
- [PIL/Pillow](https://pillow.readthedocs.io/)

## Troubleshooting

### Common Issues

**"ffmpeg not found"**
- Install ffmpeg: `apt install ffmpeg` or `brew install ffmpeg`
- Add ffmpeg to PATH

**"Out of memory" errors**
- Process video in chunks
- Reduce resolution/quality
- Use streaming instead of loading full files

**Slow rendering**
- Use hardware acceleration if available
- Optimize codec settings
- Consider cloud processing for large batches

## Questions to Ask Before Implementation

When starting new work, clarify:
1. What audio formats should be supported?
2. What's the target video resolution and format?
3. Should this work offline or require internet?
4. What's the acceptable processing time?
5. Are there budget constraints for API usage?
6. What platforms must this run on?

## Updating This Document

Keep CLAUDE.md current as the project evolves:
- Update structure when directories change
- Document new conventions as they're established
- Add troubleshooting entries for recurring issues
- Keep dependency information accurate
- Update examples to reflect current API

---

**Last Updated**: 2025-11-14
**Project Stage**: Initial setup
**Primary Contributors**: To be determined

For questions or suggestions about this guide, open an issue or update this file directly.
