"""
Subtitle downloading, conversion, and management.
"""
import os
import re
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None


@dataclass
class Subtitle:
    """Subtitle file information."""
    language: str
    url: str
    format: str  # 'srt', 'vtt', 'ttml', etc.
    name: Optional[str] = None
    is_default: bool = False
    is_forced: bool = False
    downloaded_path: Optional[str] = None


class SubtitleManager:
    """Manage subtitle operations."""
    
    SUPPORTED_FORMATS = ['vtt', 'srt', 'ttml', 'dfxp', 'ass', 'ssa']
    
    def __init__(self, output_dir: str, headers: Dict[str, str] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.subtitles: List[Subtitle] = []
    
    async def download_subtitle(self, subtitle: Subtitle, 
                                video_filename: str = None) -> Optional[str]:
        """Download a single subtitle file."""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp is required for subtitle download. Install: pip install aiohttp")
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(subtitle.url, timeout=30) as response:
                    if response.status != 200:
                        return None
                    
                    content = await response.text()
                    
                    # Determine filename
                    if video_filename:
                        base_name = Path(video_filename).stem
                    else:
                        base_name = "subtitle"
                    
                    ext = subtitle.format if subtitle.format in self.SUPPORTED_FORMATS else 'vtt'
                    filename = f"{base_name}.{subtitle.language}.{ext}"
                    filepath = self.output_dir / filename
                    
                    # Convert VTT to SRT if needed
                    if ext == 'vtt':
                        content = self._convert_vtt_to_srt(content)
                        filepath = self.output_dir / f"{base_name}.{subtitle.language}.srt"
                    
                    # Save file
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    subtitle.downloaded_path = str(filepath)
                    return str(filepath)
                    
        except Exception as e:
            print(f"[-] Failed to download subtitle: {e}")
            return None
    
    async def download_all(self, subtitles: List[Subtitle],
                          video_filename: str = None) -> List[str]:
        """Download all subtitles."""
        downloaded = []
        for sub in subtitles:
            path = await self.download_subtitle(sub, video_filename)
            if path:
                downloaded.append(path)
        return downloaded
    
    def _convert_vtt_to_srt(self, vtt_content: str) -> str:
        """Convert WebVTT to SRT format."""
        lines = vtt_content.split('\n')
        srt_lines = []
        cue_count = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip WEBVTT header and metadata
            if line.startswith('WEBVTT') or line.startswith('NOTE') or line.startswith('REGION'):
                i += 1
                continue
            
            # Check for timestamp line (00:00:00.000 --> 00:00:00.000)
            timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})', line)
            if timestamp_match:
                cue_count += 1
                start = timestamp_match.group(1).replace('.', ',')
                end = timestamp_match.group(2).replace('.', ',')
                srt_lines.append(str(cue_count))
                srt_lines.append(f"{start} --> {end}")
                
                # Collect text lines until blank line
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    # Remove VTT voice tags like <v Speaker>
                    text = re.sub(r'<v[^>]*>', '', lines[i])
                    text = re.sub(r'</v>', '', text)
                    text_lines.append(text)
                    i += 1
                
                srt_lines.extend(text_lines)
                srt_lines.append('')
            else:
                i += 1
        
        return '\n'.join(srt_lines)
    
    def embed_subtitles(self, video_path: str, subtitle_paths: List[str],
                       output_path: str = None) -> Optional[str]:
        """
        Embed subtitles into video file using ffmpeg.
        
        Returns:
            Path to output video file
        """
        import subprocess
        
        if not subtitle_paths:
            return None
        
        if not output_path:
            base = Path(video_path).stem
            output_path = str(self.output_dir / f"{base}_with_subs.mp4")
        
        # Build ffmpeg command
        cmd = ['ffmpeg', '-i', video_path, '-y']
        
        # Add subtitle inputs
        for sub_path in subtitle_paths:
            cmd.extend(['-i', sub_path])
        
        # Map video and audio from first input
        cmd.extend(['-map', '0:v', '-map', '0:a'])
        
        # Map subtitle streams
        for i in range(len(subtitle_paths)):
            cmd.extend(['-map', f'{i+1}:s'])
        
        # Codec settings
        cmd.extend([
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-c:s', 'mov_text',  # For MP4 container
            '-metadata:s:s:0', 'language=eng'
        ])
        
        cmd.append(output_path)
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to embed subtitles: {e}")
            return None
    
    def burn_subtitles(self, video_path: str, subtitle_path: str,
                      output_path: str = None) -> Optional[str]:
        """
        Hardcode/burn subtitles into video frames.
        
        Returns:
            Path to output video file
        """
        import subprocess
        
        if not output_path:
            base = Path(video_path).stem
            output_path = str(self.output_dir / f"{base}_burned.mp4")
        
        # Escape subtitle path for ffmpeg filter
        escaped_subs = subtitle_path.replace('\\', '\\\\').replace(':', '\\:')
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f"subtitles='{escaped_subs}'",
            '-c:a', 'copy',
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to burn subtitles: {e}")
            return None
    
    def extract_subtitles_from_video(self, video_path: str) -> List[str]:
        """Extract embedded subtitles from video file."""
        import subprocess
        import json
        
        # Get subtitle streams info
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            subtitle_files = []
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'subtitle':
                    index = stream.get('index')
                    lang = stream.get('tags', {}).get('language', 'unknown')
                    
                    # Extract this subtitle stream
                    output_sub = str(self.output_dir / f"extracted_{lang}_{index}.srt")
                    
                    extract_cmd = [
                        'ffmpeg',
                        '-i', video_path,
                        '-map', f'0:{index}',
                        '-y',
                        output_sub
                    ]
                    
                    subprocess.run(extract_cmd, capture_output=True)
                    
                    if Path(output_sub).exists():
                        subtitle_files.append(output_sub)
            
            return subtitle_files
            
        except Exception as e:
            print(f"[-] Failed to extract subtitles: {e}")
            return []
    
    def auto_translate(self, subtitle_path: str, target_lang: str = 'en') -> Optional[str]:
        """
        Auto-translate subtitle using Google Translate or similar.
        
        Note: This is a placeholder for future implementation.
        """
        # TODO: Implement translation using Google Translate API or similar
        print(f"[*] Auto-translate to {target_lang} not yet implemented")
        return None
