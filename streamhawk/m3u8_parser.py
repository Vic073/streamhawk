"""
M3U8/HLS playlist parser for quality selection.
"""
import re
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None


@dataclass
class M3U8Stream:
    """Represents a single stream variant in a master playlist."""
    bandwidth: int
    resolution: Optional[str] = None
    codecs: Optional[str] = None
    url: Optional[str] = None
    frame_rate: Optional[float] = None
    audio: Optional[str] = None
    video: Optional[str] = None
    
    @property
    def height(self) -> int:
        """Extract height from resolution string."""
        if not self.resolution:
            return 0
        match = re.search(r'(\d+)', self.resolution)
        return int(match.group(1)) if match else 0
    
    @property
    def width(self) -> int:
        """Extract width from resolution string."""
        if not self.resolution:
            return 0
        match = re.search(r'(\d+)x(\d+)', self.resolution)
        if match:
            return int(match.group(1))
        return 0
    
    def __repr__(self) -> str:
        return f"M3U8Stream({self.resolution or 'unknown'}, {self.bandwidth}bps)"


@dataclass
class M3U8Subtitle:
    """Represents a subtitle stream."""
    language: str
    name: str
    url: str
    group_id: Optional[str] = None
    default: bool = False
    forced: bool = False


@dataclass
class M3U8Audio:
    """Represents an audio stream."""
    language: str
    name: str
    url: Optional[str] = None
    group_id: Optional[str] = None
    default: bool = False
    codec: Optional[str] = None


class M3U8Parser:
    """Parser for M3U8/HLS playlist files."""
    
    def __init__(self, headers: Dict[str, str] = None):
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.streams: List[M3U8Stream] = []
        self.subtitles: List[M3U8Subtitle] = []
        self.audio_tracks: List[M3U8Audio] = []
        self.is_master = False
        self.media_sequence = 0
        self.target_duration = 0
        self.version = 3
    
    async def parse_from_url(self, url: str) -> 'M3U8Parser':
        """Fetch and parse M3U8 from URL."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp is required for URL parsing. Install: pip install aiohttp")
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, timeout=30) as response:
                content = await response.text()
                return self.parse(content, base_url=url)
    
    def parse(self, content: str, base_url: str = None) -> 'M3U8Parser':
        """Parse M3U8 content."""
        lines = content.strip().split('\n')
        
        if not lines or not lines[0].startswith('#EXTM3U'):
            raise ValueError("Invalid M3U8 file - missing #EXTM3U header")
        
        current_stream = None
        current_audio = None
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Master playlist detection
            if '#EXT-X-STREAM-INF' in line:
                self.is_master = True
                current_stream = self._parse_stream_info(line)
                
            elif '#EXT-X-MEDIA' in line and 'TYPE=SUBTITLES' in line:
                subtitle = self._parse_media_subtitle(line, base_url)
                if subtitle:
                    self.subtitles.append(subtitle)
                    
            elif '#EXT-X-MEDIA' in line and 'TYPE=AUDIO' in line:
                audio = self._parse_media_audio(line)
                if audio:
                    self.audio_tracks.append(audio)
                    
            elif line.startswith('#EXT-X-TARGETDURATION'):
                match = re.search(r':(\d+)', line)
                if match:
                    self.target_duration = int(match.group(1))
                    
            elif line.startswith('#EXT-X-MEDIA-SEQUENCE'):
                match = re.search(r':(\d+)', line)
                if match:
                    self.media_sequence = int(match.group(1))
                    
            elif line.startswith('#EXT-X-VERSION'):
                match = re.search(r':(\d+)', line)
                if match:
                    self.version = int(match.group(1))
                    
            elif not line.startswith('#'):
                # This is a URL line
                url = line
                if base_url and not url.startswith('http'):
                    url = urljoin(base_url, url)
                
                if current_stream:
                    current_stream.url = url
                    self.streams.append(current_stream)
                    current_stream = None
                    
            i += 1
        
        return self
    
    def _parse_stream_info(self, line: str) -> M3U8Stream:
        """Parse #EXT-X-STREAM-INF line."""
        stream = M3U8Stream(bandwidth=0)
        
        # Extract bandwidth (required)
        match = re.search(r'BANDWIDTH=(\d+)', line)
        if match:
            stream.bandwidth = int(match.group(1))
        
        # Extract resolution
        match = re.search(r'RESOLUTION=(\d+x\d+)', line)
        if match:
            stream.resolution = match.group(1)
        
        # Extract codecs
        match = re.search(r'CODECS="([^"]+)"', line)
        if match:
            stream.codecs = match.group(1)
        
        # Extract frame rate
        match = re.search(r'FRAME-RATE=([\d.]+)', line)
        if match:
            stream.frame_rate = float(match.group(1))
        
        # Extract audio group
        match = re.search(r'AUDIO="([^"]+)"', line)
        if match:
            stream.audio = match.group(1)
        
        # Extract video group
        match = re.search(r'VIDEO="([^"]+)"', line)
        if match:
            stream.video = match.group(1)
        
        return stream
    
    def _parse_media_subtitle(self, line: str, base_url: str) -> Optional[M3U8Subtitle]:
        """Parse subtitle media info."""
        try:
            language = self._extract_attribute(line, 'LANGUAGE') or 'unknown'
            name = self._extract_attribute(line, 'NAME') or language
            uri = self._extract_attribute(line, 'URI')
            group_id = self._extract_attribute(line, 'GROUP-ID')
            default = 'DEFAULT=YES' in line
            forced = 'FORCED=YES' in line
            
            if uri and base_url and not uri.startswith('http'):
                uri = urljoin(base_url, uri)
            
            return M3U8Subtitle(
                language=language,
                name=name,
                url=uri,
                group_id=group_id,
                default=default,
                forced=forced
            )
        except Exception:
            return None
    
    def _parse_media_audio(self, line: str) -> Optional[M3U8Audio]:
        """Parse audio media info."""
        try:
            language = self._extract_attribute(line, 'LANGUAGE') or 'unknown'
            name = self._extract_attribute(line, 'NAME') or language
            group_id = self._extract_attribute(line, 'GROUP-ID')
            uri = self._extract_attribute(line, 'URI')
            default = 'DEFAULT=YES' in line
            
            return M3U8Audio(
                language=language,
                name=name,
                url=uri,
                group_id=group_id,
                default=default
            )
        except Exception:
            return None
    
    def _extract_attribute(self, line: str, attr: str) -> Optional[str]:
        """Extract attribute value from line."""
        pattern = rf'{attr}="([^"]+)"'
        match = re.search(pattern, line)
        if match:
            return match.group(1)
        
        # Try without quotes
        pattern = rf'{attr}=([^,\s]+)'
        match = re.search(pattern, line)
        if match:
            return match.group(1)
        
        return None
    
    def get_best_stream(self, max_resolution: str = None) -> Optional[M3U8Stream]:
        """Get best quality stream, optionally limited by resolution."""
        if not self.streams:
            return None
        
        if max_resolution:
            max_height = self._parse_resolution_height(max_resolution)
            # Filter streams by max resolution
            valid_streams = [s for s in self.streams if s.height <= max_height]
            if valid_streams:
                # Return highest bandwidth stream within resolution limit
                return max(valid_streams, key=lambda s: s.bandwidth)
        
        # Return stream with highest bandwidth
        return max(self.streams, key=lambda s: s.bandwidth)
    
    def get_stream_by_resolution(self, resolution: str) -> Optional[M3U8Stream]:
        """Get stream matching specific resolution."""
        target_height = self._parse_resolution_height(resolution)
        
        # Find closest match
        best_match = None
        best_diff = float('inf')
        
        for stream in self.streams:
            diff = abs(stream.height - target_height)
            if diff < best_diff:
                best_diff = diff
                best_match = stream
        
        return best_match
    
    def get_available_qualities(self) -> List[str]:
        """Get list of available quality options."""
        qualities = []
        for stream in self.streams:
            if stream.resolution:
                qualities.append(stream.resolution)
            elif stream.bandwidth:
                # Estimate resolution from bandwidth
                qualities.append(self._bandwidth_to_quality(stream.bandwidth))
        return qualities
    
    def _parse_resolution_height(self, resolution: str) -> int:
        """Parse resolution string to height."""
        resolution = resolution.lower()
        
        # Handle common formats
        if 'x' in resolution:
            parts = resolution.split('x')
            return int(parts[1]) if len(parts) > 1 else int(parts[0])
        
        if 'p' in resolution:
            return int(resolution.replace('p', ''))
        
        # Handle named resolutions
        heights = {
            '4k': 2160, 'uhd': 2160,
            '1080p': 1080, 'fhd': 1080,
            '720p': 720, 'hd': 720,
            '480p': 480, 'sd': 480,
            '360p': 360,
            '240p': 240,
            '144p': 144
        }
        
        return heights.get(resolution, 1080)
    
    def _bandwidth_to_quality(self, bandwidth: int) -> str:
        """Estimate quality from bandwidth."""
        if bandwidth >= 15000000:
            return "4K"
        elif bandwidth >= 8000000:
            return "1080p"
        elif bandwidth >= 4000000:
            return "720p"
        elif bandwidth >= 1500000:
            return "480p"
        elif bandwidth >= 800000:
            return "360p"
        else:
            return "240p"
    
    def download_subtitles(self, output_dir: str) -> List[str]:
        """Download all subtitle files."""
        # TODO: Implement subtitle download
        return []
    
    def __repr__(self) -> str:
        return f"M3U8Parser(streams={len(self.streams)}, subtitles={len(self.subtitles)}, audio={len(self.audio_tracks)})"
