"""
Configuration management for StreamHawk.
"""
import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, List


@dataclass
class Config:
    """Configuration dataclass with defaults."""
    
    # Browser settings
    headless: bool = True
    browser_timeout: int = 45
    page_load_timeout: int = 30
    
    # Download settings
    download_dir: str = field(default_factory=lambda: str(Path.home() / "Downloads" / "StreamHawk"))
    default_quality: str = "best"  # best, 1080p, 720p, 480p, 360p
    output_template: str = "%(title)s (%(year)s).%(ext)s"
    auto_add_extension: bool = True
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 5
    fragment_retries: int = 10
    
    # Proxy settings
    proxy: Optional[str] = None  # http://host:port or socks5://host:port
    use_rotating_proxies: bool = False
    proxy_list: List[str] = field(default_factory=list)
    
    # Features
    auto_resume: bool = True
    save_history: bool = True
    fetch_metadata: bool = True
    extract_subtitles: bool = False
    burn_subtitles: bool = False
    
    # Network
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    request_delay: float = 1.0
    
    # Logging
    log_level: str = "INFO"
    log_dir: str = field(default_factory=lambda: str(Path.home() / ".streamhawk" / "logs"))
    save_debug_logs: bool = False
    
    # Notifications
    desktop_notifications: bool = False
    webhook_url: Optional[str] = None
    
    # yt-dlp options
    ytdlp_extra_args: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Ensure directories exist."""
        Path(self.download_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_file(cls, path: str = "config.json") -> "Config":
        """Load configuration from JSON file."""
        if not os.path.exists(path):
            return cls()
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Filter only valid fields
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)
    
    def save(self, path: str = "config.json") -> None:
        """Save configuration to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2)
    
    def get_proxy(self) -> Optional[str]:
        """Get current proxy (rotating or fixed)."""
        if not self.use_rotating_proxies or not self.proxy_list:
            return self.proxy
        import random
        return random.choice(self.proxy_list)