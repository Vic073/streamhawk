# StreamHawk v2.0 - Project Summary

## Modern Modular Architecture

The project follows a standard `src/` layout with a consolidated configuration system.

### Core Modules (`src/streamhawk/`)

| Module | Purpose | Features |
|--------|---------|----------|
| [main.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/main.py) | Application Entry | Core logic orchestration |
| [metadata.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/metadata.py) | Metadata Fetch | IMDb scraping and API integration |
| [hls.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/hls.py) | Playlist Parser | HLS manifest analysis and quality selection |
| [browser.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/browser.py) | Stealth Browser | Anti-detection, ad-blocking, proxy support |
| [extractor.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/extractor.py) | Stream Capture | Network interception and HLS discovery |
| [downloader.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/downloader.py) | yt-dlp Manager | Multi-threaded downloads and resume support |
| [config.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/config.py) | Configuration | Dataclass-based settings management |
| [cli.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/cli.py) | Terminal UI | Interactive prompts and batch processing |
| [notifications.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/notifications.py) | Alerts | Desktop and webhook notifications |
| [utils.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/utils.py) | Utilities | Logging, history, and string helpers |
| [__init__.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/src/streamhawk/__init__.py) | Package Exports | Clean public API definition |

### Testing Suite

- [test_config.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/tests/test_config.py) - Configuration validation
- [test_utils.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/tests/test_utils.py) - Utility logic tests
- [test_hls.py](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/tests/test_hls.py) - HLS manifest parsing tests

### Docker Support

- `.dockerignore` - Build optimization
- `Dockerfile` - Multi-stage container builds
- `docker-compose.yml` - Local service orchestration

### Configuration & Deployment

- `config.json` - Default runtime settings
- [pyproject.toml](file:///c:/Users/Victor%20Chilomo/OneDrive/Desktop/New%20folder/pyproject.toml) - Modern build system and dependency management

### Documentation & Assets

- `README.md` - Getting started guide
- `PROJECT_SUMMARY.md` - Technical overview
- `movies.txt` - Batch processing template

## Features Implemented

### 1. Stream Extraction
- Automated HLS .m3u8 discovery
- Network traffic interception with predicate filtering
- Quality-aware manifest parsing
- Automatic header preservation (Referer, User-Agent)

### 2. Download Management
- Native yt-dlp integration
- Automatic download resumption
- Real-time progress tracking
- Custom output templates

### 3. Anti-Detection & Stealth
- WebDriver property masking
- Chrome runtime API emulation
- Ad-popup auto-suppression
- Custom User-Agent rotation

### 4. User Experience
- Interactive CLI with colored output
- Desktop notifications for completion/failure
- History tracking for past extractions

## Usage Examples

```bash
# Direct command (if installed via pip)
streamhawk --imdb tt0816692

# Via Python module
python -m streamhawk.main --imdb tt0816692
```

## Module Dependencies

```
main.py
  ├─ cli.py
  │   ├─ config.py
  │   └─ utils.py
  ├─ extractor.py
  │   ├─ browser.py
  │   ├─ config.py
  │   └─ hls.py
  ├─ downloader.py
  │   ├─ config.py
  │   └─ utils.py
  ├─ metadata.py
  ├─ notifications.py
  └─ utils.py
```

## Maintenance & Standards

- **PEP 517/518 Compliance**: Uses `pyproject.toml` for builds.
- **Source Layout**: Adheres to the standard `src/` directory pattern.
- **Testing**: Automated test suite with `pytest`.
- **Clean Code**: Removed redundant modules (fingerprints, postprocessor, subtitles) to maintain a lean core.
