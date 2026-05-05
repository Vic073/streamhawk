# Project Horizon - HLS Stream Extractor

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Playwright](https://img.shields.io/badge/playwright-green.svg)](https://playwright.dev/python/)

An automated command-line tool that extracts HLS stream manifests (.m3u8) from third-party IMDb mirrors and hands them off to [yt-dlp](https://github.com/yt-dlp/yt-dlp) for downloading.

> **Disclaimer:** This tool is for educational purposes regarding HLS protocol analysis and browser automation. Users are responsible for adhering to local copyright laws and the Terms of Service of targeted websites.

---

## Features

- **Interactive Terminal Interface** - Simply paste an IMDb URL or ID
- **Anti-Detection Bypass** - Advanced evasion for disable-devtool scripts and bot detection
- **Network Traffic Monitoring** - Real-time interception of XHR/Fetch requests
- **Automatic Header Capture** - Extracts Referer and User-Agent for valid stream requests
- **Pop-up Management** - Auto-closes ad-triggered popups
- **404 Resilience** - Graceful handling of missing movies or server errors
- **Headless Mode Toggle** - Debug mode for visual browser inspection

---

## Requirements

- **Python 3.10+**
- [Playwright](https://playwright.dev/python/) - Browser automation
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Stream downloader
- [ffmpeg](https://ffmpeg.org/) - Stream muxer (optional, for format conversion)

---

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/Vic073/streamhawk.git
cd streamhawk
```

2. **Install the package:**
```bash
pip install .
```
This will automatically install all core dependencies including Playwright and yt-dlp.

3. **Install browser binaries:**
```bash
playwright install chromium
```

4. **Install ffmpeg** (optional but recommended):
- Windows: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

---

## Usage

You can run the tool using the command-line entry points:

```bash
streamhawk
```
or
```bash
shawk
```

Alternatively, you can run it via Python:

```bash
python -m streamhawk.main
```

---

## Input Formats

The tool accepts various IMDb identifier formats:

| Input | Valid |
|-------|-------|
| `tt0816692` | Direct IMDb ID |
| `https://www.imdb.com/title/tt0816692/` | Full IMDb URL |
| `imdb.com/title/tt0816692` | Partial URL |
| `imdb.com/Title?tt0816692` | Legacy format |

---

## Technical Architecture

### Phase A: The Stealth Navigator
- **User-Agent Spooling:** Real-world Chrome user agent string
- **WebDriver Masking:** Removes `navigator.webdriver` property
- **Chrome Runtime Emulation:** Fakes Chrome-specific APIs
- **Permissions Override:** Prevents notification permission probing
- **DevTool Detection Bypass:** Neutralizes debugger timing attacks
- **Pop-up Management:** Auto-closes revenue-triggered windows

### Phase B: The Traffic Monitor
- **Predicate Filtering:** Listens for URLs containing `.m3u8`
- **Ad Exclusion:** Filters out URLs containing "ads" or "advert"
- **Persistence:** Active until manifest captured or timeout (45s default)

### Phase C: The Handoff
- **Header Preservation:** Captures Referer and User-Agent
- **yt-dlp Integration:** Subprocess invocation with proper headers
- **HLS Options:** MPEGTS format, retry logic for reliability

---

## Troubleshooting

### Issue: "yt-dlp not found"
**Solution:** Install yt-dlp: `pip install yt-dlp`

### Issue: "Timeout: No HLS stream detected"
**Possible causes:**
- Movie not available on the mirror
- Anti-bot protection triggered
- Stream uses different protocol

**Solution:** Try running with headful mode (`n` at the headless prompt) to see what's happening.

### Issue: "Movie not found in database (404)"
**Solution:** The IMDb ID exists but the movie isn't indexed by the mirror. Try a different title.

### Issue: Download fails with yt-dlp
**Solution:** Ensure ffmpeg is installed for stream muxing.

---

## Browser Launch Arguments

The tool uses the following Chromium flags for stealth:

```python
--disable-dev-shm-usage
--no-sandbox
--disable-blink-features=AutomationControlled
--disable-features=IsolateOrigins,site-per-process
--disable-web-security
--disable-features=BlockInsecurePrivateNetworkRequests
```

---

## Security & Ethics

- **Educational Purpose:** This tool demonstrates HLS protocol analysis and browser automation techniques.
- **User Responsibility:** You are solely responsible for compliance with local copyright laws and website Terms of Service.
- **No Warranties:** This software is provided "as is" without warranty of any kind.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## Acknowledgments

- [Playwright](https://playwright.dev/) - Browser automation framework
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Feature-rich media downloader
- [ffmpeg](https://ffmpeg.org/) - Complete solution for media handling

---

## Disclaimer

> This project is intended for educational purposes only. The author do not condone or encourage any illegal activities, including copyright infringement. Users are responsible for ensuring their use of this software complies with all applicable laws and regulations in their jurisdiction.
