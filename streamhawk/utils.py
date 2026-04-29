"""
Utility functions and logging setup.
"""
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        record.levelname = f"{log_color}{record.levelname}{reset}"
        return super().format(record)


def setup_logger(name: str = "streamhawk", log_dir: Optional[str] = None, 
                 level: str = "INFO", save_to_file: bool = False) -> logging.Logger:
    """Setup logger with file and console handlers."""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers = []  # Clear existing handlers
    
    # Console handler with colors
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console_fmt = ColoredFormatter('%(levelname)s - %(message)s')
    console.setFormatter(console_fmt)
    logger.addHandler(console)
    
    # File handler (if enabled)
    if save_to_file and log_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = Path(log_dir) / f"streamhawk_{timestamp}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
    
    return logger


# Global logger instance
logger = setup_logger()


def extract_imdb_id(url_or_id: str) -> Optional[str]:
    """Extract IMDb ID from URL or validate direct ID input."""
    url_or_id = url_or_id.strip()
    
    # Direct IMDb ID pattern
    if re.match(r"^tt\d+$", url_or_id):
        return url_or_id
    
    # Extract from IMDb URL patterns
    patterns = [
        r"imdb\.com/title/(tt\d+)",
        r"imdb\.com/Title\?(tt\d+)",
        r"/title/(tt\d+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = "".join(char for char in filename if ord(char) >= 32)
    
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200] + ext
    
    return filename.strip()


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def parse_quality(quality_str: str) -> int:
    """Parse quality string to numeric value for comparison."""
    qualities = {
        'best': 9999,
        '4k': 2160,
        '2160p': 2160,
        '1440p': 1440,
        '1080p': 1080,
        '720p': 720,
        '480p': 480,
        '360p': 360,
        '240p': 240,
        'worst': 0
    }
    return qualities.get(quality_str.lower(), 1080)


class HistoryManager:
    """Manage download history."""
    
    def __init__(self, history_file: str = None):
        if history_file is None:
            history_file = str(Path.home() / ".streamhawk" / "history.json")
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()
    
    def _load(self) -> list:
        """Load history from file."""
        if not self.history_file.exists():
            return []
        import json
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def save(self) -> None:
        """Save history to file."""
        import json
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)
    
    def add(self, imdb_id: str, title: str, status: str, 
            m3u8_url: str = None, output_file: str = None) -> None:
        """Add entry to history."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'imdb_id': imdb_id,
            'title': title,
            'status': status,  # 'success', 'failed', 'cancelled'
            'm3u8_url': m3u8_url,
            'output_file': output_file
        }
        self._data.append(entry)
        self.save()
    
    def get_recent(self, limit: int = 10) -> list:
        """Get recent history entries."""
        return self._data[-limit:][::-1]
    
    def find_by_imdb(self, imdb_id: str) -> list:
        """Find history entries by IMDb ID."""
        return [e for e in self._data if e['imdb_id'] == imdb_id]