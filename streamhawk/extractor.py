"""
HLS Stream extraction module.
"""
import asyncio
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

from .browser import StealthBrowser, RequestInterceptor
from .config import Config
from .utils import logger


@dataclass
class StreamInfo:
    """Stream information dataclass."""
    url: str
    headers: Dict[str, str]
    quality: Optional[str] = None
    is_master: bool = False
    bandwidth: Optional[int] = None
    resolution: Optional[str] = None
    codec: Optional[str] = None


class QualitySelector:
    """Selects best quality from available streams."""
    
    QUALITY_ORDER = {
        '4k': 2160, '2160p': 2160, 'uhd': 2160,
        '1440p': 1440, '2k': 1440,
        '1080p': 1080, 'fhd': 1080,
        '720p': 720, 'hd': 720,
        '480p': 480, 'sd': 480,
        '360p': 360,
        '240p': 240,
        '144p': 144
    }
    
    @classmethod
    def parse_resolution(cls, resolution_str: str) -> int:
        """Parse resolution string to numeric value."""
        if not resolution_str:
            return 0
        
        resolution_str = resolution_str.lower().replace('x', 'p')
        
        # Try to extract number
        import re
        match = re.search(r'(\d+)(?:p|x\d+)?', resolution_str)
        if match:
            height = int(match.group(1))
            if height > 1000:  # Likely width, convert to height
                return 0
            return height
        
        return cls.QUALITY_ORDER.get(resolution_str, 0)
    
    @classmethod
    def select_best(cls, streams: List[StreamInfo], 
                    preferred_quality: str = "best") -> Optional[StreamInfo]:
        """Select best stream based on preference."""
        if not streams:
            return None
        
        if preferred_quality == "best":
            # Sort by resolution descending
            return max(streams, key=lambda s: cls.parse_resolution(s.resolution or '0p'))
        
        if preferred_quality == "worst":
            return min(streams, key=lambda s: cls.parse_resolution(s.resolution or '9999p'))
        
        # Find closest to preferred quality
        target_height = cls.parse_resolution(preferred_quality)
        
        # Sort by distance from target
        sorted_streams = sorted(
            streams, 
            key=lambda s: abs(cls.parse_resolution(s.resolution or '0p') - target_height)
        )
        
        return sorted_streams[0] if sorted_streams else None


class StreamExtractor:
    """Main stream extraction class."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.interceptor = RequestInterceptor(
            target_extensions=['.m3u8', '.mpd', '.m3u'],
            exclude_patterns=['ads', 'advert', 'tracking', 'analytics', 'stats']
        )
        self.captured_stream: Optional[StreamInfo] = None
        self._captured_event = asyncio.Event()
        
    def _create_request_handler(self):
        """Create request handler that captures streams."""
        async def on_stream_captured(url: str, headers: Dict):
            logger.info(f"HLS manifest captured: {url[:80]}...")
            
            is_master = 'master' in url.lower()
            
            self.captured_stream = StreamInfo(
                url=url,
                headers={
                    'User-Agent': self.config.user_agent,
                    'Referer': headers.get('referer', ''),
                    'Origin': headers.get('origin', '')
                },
                is_master=is_master
            )
            self._captured_event.set()
        
        return self.interceptor.create_handler(on_stream_captured)
    
    async def extract(self, target_url: str, 
                      progress_callback: callable = None) -> Tuple[Optional[StreamInfo], Optional[str]]:
        """
        Extract HLS stream from target URL.
        
        Args:
            target_url: URL to extract stream from
            progress_callback: Optional callback(status_message)
            
        Returns:
            Tuple of (StreamInfo, error_message)
        """
        self.captured_stream = None
        self._captured_event.clear()
        self.interceptor.clear()
        
        proxy = self.config.get_proxy()
        
        try:
            async with StealthBrowser(
                headless=self.config.headless,
                proxy=proxy,
                user_agent=self.config.user_agent,
                timeout=self.config.page_load_timeout * 1000
            ) as browser:
                
                # Register request handler
                browser.on_request(self._create_request_handler())
                
                if progress_callback:
                    progress_callback("Navigating to target...")
                
                # Navigate to page
                response = await browser.goto(target_url)
                
                # Check response status
                if response:
                    if response.status == 404:
                        return None, "Movie not found in database (404)"
                    elif response.status >= 400:
                        return None, f"Server error: HTTP {response.status}"
                
                if progress_callback:
                    progress_callback("Waiting for stream to load...")
                
                # Wait for stream capture or timeout
                try:
                    await asyncio.wait_for(
                        self._captured_event.wait(),
                        timeout=self.config.browser_timeout
                    )
                except asyncio.TimeoutError:
                    # Check if we have any captured URLs
                    if not self.captured_stream:
                        # Check page content for error indicators
                        content = await browser.content()
                        error_indicators = ['not found', '404', 'error', 'unavailable', 'removed']
                        
                        if any(ind in content.lower() for ind in error_indicators):
                            return None, "Movie not available (content indicates error)"
                        
                        return None, "Timeout: No HLS stream detected within time limit"
                
                # If master playlist, parse for qualities
                if self.captured_stream and self.captured_stream.is_master:
                    if progress_callback:
                        progress_callback("Parsing quality options...")
                    
                    # TODO: Implement master playlist parsing
                    pass
                
                return self.captured_stream, None
                
        except PlaywrightTimeoutError:
            return None, "Page load timeout - site may be slow or blocking"
        except Exception as e:
            logger.exception("Extraction failed")
            return None, f"Extraction error: {str(e)}"
    
    async def extract_with_retry(self, target_url: str, 
                                  progress_callback: callable = None) -> Tuple[Optional[StreamInfo], Optional[str]]:
        """Extract with automatic retry."""
        for attempt in range(1, self.config.max_retries + 1):
            if progress_callback and attempt > 1:
                progress_callback(f"Retry attempt {attempt}/{self.config.max_retries}...")
            
            stream, error = await self.extract(target_url, progress_callback)
            
            if stream:
                return stream, None
            
            if attempt < self.config.max_retries:
                logger.warning(f"Attempt {attempt} failed: {error}. Retrying...")
                await asyncio.sleep(self.config.retry_delay * attempt)
        
        return None, error
    
    async def preview_stream(self, stream_info: StreamInfo, 
                            duration_seconds: int = 10) -> bool:
        """
        Preview stream by downloading first few seconds.
        
        Returns:
            True if preview successful
        """
        # TODO: Implement preview using yt-dlp partial download
        logger.info("Stream preview not yet implemented")
        return True
    
    def get_stream_qualities(self, master_url: str) -> List[StreamInfo]:
        """Parse master playlist and return available qualities."""
        # TODO: Implement m3u8 parsing
        return [self.captured_stream] if self.captured_stream else []