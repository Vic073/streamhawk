"""
yt-dlp download manager with resume and quality selection support.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

from .config import Config
from .extractor import StreamInfo
from .utils import logger, sanitize_filename


@dataclass
class DownloadProgress:
    """Download progress information."""
    percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed: str = ""
    eta: str = ""
    status: str = "pending"  # pending, downloading, complete, error


class YTDLPManager:
    """Manager for yt-dlp operations."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self._check_ytdlp()
    
    def _check_ytdlp(self) -> bool:
        """Check if yt-dlp is installed."""
        try:
            subprocess.run(["yt-dlp", "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("yt-dlp not found. Install: pip install yt-dlp")
    
    def _build_command(self, stream_info: StreamInfo, 
                       output_path: str,
                       quality: str = None,
                       extra_args: List[str] = None) -> List[str]:
        """Build yt-dlp command."""
        
        cmd = [
            "yt-dlp",
            # Headers
            "--referer", stream_info.headers.get('Referer', ''),
            "--user-agent", stream_info.headers.get('User-Agent', self.config.user_agent),
            "--add-header", f"Referer:{stream_info.headers.get('Referer', '')}",
            "--add-header", f"Origin:{stream_info.headers.get('Origin', '')}",
            
            # Format selection
            "--format", "best" if quality == "best" else f"best[height<={self._parse_quality_height(quality)}]" if quality else "best",
            
            # HLS options
            "--hls-use-mpegts",
            "--fragment-retries", str(self.config.fragment_retries),
            "--retries", str(self.config.max_retries),
            
            # Resume support
            "--continue" if self.config.auto_resume else "",
            "--no-overwrites",
            
            # Subtitles
            "--embed-subs" if self.config.extract_subtitles else "",
            "--sub-langs", "en" if self.config.extract_subtitles else "",
            
            # Post-processing
            "--remux-video", "mp4" if not self.config.burn_subtitles else "",
            "--embed-metadata",
            "--embed-thumbnail",
            
            # Output
            "-o", output_path,
            
            # Progress
            "--newline",
            "--progress",
            "--console-title" if os.name == 'nt' else "",
        ]
        
        # Proxy
        proxy = self.config.get_proxy()
        if proxy:
            cmd.extend(["--proxy", proxy])
        
        # Extra args from config
        if self.config.ytdlp_extra_args:
            cmd.extend(self.config.ytdlp_extra_args)
        
        # Extra args from call
        if extra_args:
            cmd.extend(extra_args)
        
        # Remove empty strings
        cmd = [arg for arg in cmd if arg]
        
        # Stream URL
        cmd.append(stream_info.url)
        
        return cmd
    
    def _parse_quality_height(self, quality: str) -> int:
        """Parse quality string to height."""
        if not quality or quality == "best":
            return 2160
        
        heights = {
            '4k': 2160, '2160p': 2160,
            '1440p': 1440,
            '1080p': 1080,
            '720p': 720,
            '480p': 480,
            '360p': 360
        }
        
        return heights.get(quality.lower(), 1080)
    
    def download(self, stream_info: StreamInfo,
                 output_name: str = None,
                 quality: str = None,
                 progress_callback: Callable[[DownloadProgress], None] = None,
                 extra_args: List[str] = None) -> bool:
        """
        Download stream using yt-dlp.
        
        Args:
            stream_info: Stream information
            output_name: Output filename (optional)
            quality: Preferred quality (best, 1080p, 720p, etc.)
            progress_callback: Callback for progress updates
            extra_args: Additional yt-dlp arguments
            
        Returns:
            True if download successful
        """
        # Build output path
        if output_name:
            # Ensure proper extension
            if not any(output_name.endswith(ext) for ext in ['.mp4', '.mkv', '.ts', '.avi']):
                output_name += '.mp4'
            output_path = str(Path(self.config.download_dir) / sanitize_filename(output_name))
        else:
            output_path = str(Path(self.config.download_dir) / "%(title)s.%(ext)s")
        
        # Build command
        cmd = self._build_command(stream_info, output_path, quality, extra_args)
        
        logger.info(f"Starting download: {stream_info.url[:60]}...")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            # Run with progress parsing if callback provided
            if progress_callback:
                return self._download_with_progress(cmd, progress_callback, output_path)
            else:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False
    
    def _download_with_progress(self, cmd: List[str], 
                                callback: Callable[[DownloadProgress], None],
                                output_path: str) -> bool:
        """Download with progress parsing."""
        import re
        
        progress = DownloadProgress(status="downloading")
        callback(progress)
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Regex for parsing progress
        percent_re = re.compile(r'(\d+\.?\d*)%')
        size_re = re.compile(r'(\d+\.?\d*)([KMGTPE]?i?B)')
        speed_re = re.compile(r'at\s+([\d.]+\s*[KMGT]?i?B/s)')
        eta_re = re.compile(r'ETA\s+(\d+:\d+)')
        
        try:
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                
                # Parse progress
                percent_match = percent_re.search(line)
                if percent_match:
                    progress.percent = float(percent_match.group(1))
                
                # Parse size
                size_matches = list(size_re.finditer(line))
                if len(size_matches) >= 2:
                    progress.downloaded_bytes = self._parse_size(size_matches[0].group(0))
                    progress.total_bytes = self._parse_size(size_matches[1].group(0))
                
                # Parse speed
                speed_match = speed_re.search(line)
                if speed_match:
                    progress.speed = speed_match.group(1)
                
                # Parse ETA
                eta_match = eta_re.search(line)
                if eta_match:
                    progress.eta = eta_match.group(1)
                
                # Update callback
                callback(progress)
                
                # Log interesting lines
                if '[download]' in line or 'Destination' in line:
                    logger.info(line)
            
            process.wait()
            
            if process.returncode == 0:
                progress.status = "complete"
                progress.percent = 100.0
                callback(progress)
                return True
            else:
                progress.status = "error"
                callback(progress)
                return False
                
        finally:
            process.stdout.close()
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes."""
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        size_str = size_str.strip()
        for unit, multiplier in sorted(units.items(), key=lambda x: -len(x[0])):
            if unit in size_str.upper():
                try:
                    number = float(size_str.replace(unit, '').strip())
                    return int(number * multiplier)
                except ValueError:
                    continue
        
        return 0
    
    def get_available_formats(self, stream_info: StreamInfo) -> List[Dict[str, Any]]:
        """Get list of available formats for a stream."""
        try:
            cmd = [
                "yt-dlp",
                "--referer", stream_info.headers.get('Referer', ''),
                "--user-agent", stream_info.headers.get('User-Agent', ''),
                "--list-formats",
                stream_info.url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Parse output (simplified)
            formats = []
            for line in result.stdout.split('\n'):
                if 'mp4' in line or 'm3u8' in line:
                    # Extract format info (basic parsing)
                    formats.append({'info': line.strip()})
            
            return formats
            
        except Exception as e:
            logger.error(f"Failed to get formats: {e}")
            return []
    
    def verify_download(self, output_path: str) -> bool:
        """Verify downloaded file is valid."""
        path = Path(output_path)
        
        if not path.exists():
            return False
        
        if path.stat().st_size < 1024:  # Less than 1KB
            logger.warning("Downloaded file is too small")
            return False
        
        # TODO: Add ffprobe verification
        return True
    
    def resume_download(self, stream_info: StreamInfo, output_path: str) -> bool:
        """Resume interrupted download."""
        if not self.config.auto_resume:
            return False
        
        partial_file = Path(output_path + '.part')
        if not partial_file.exists():
            return False
        
        logger.info(f"Resuming download: {partial_file}")
        return self.download(stream_info, output_path, extra_args=['--continue'])
    
    def post_process(self, input_path: str, 
                     convert_to_hevc: bool = False,
                     burn_subs: bool = False) -> str:
        """
        Post-process downloaded file.
        
        Args:
            input_path: Path to downloaded file
            convert_to_hevc: Convert to HEVC/H.265
            burn_subs: Burn subtitles into video
            
        Returns:
            Path to processed file
        """
        if not convert_to_hevc and not burn_subs:
            return input_path
        
        output_path = input_path.replace('.mp4', '_processed.mp4')
        
        # Build ffmpeg command
        cmd = ["ffmpeg", "-i", input_path, "-y"]
        
        if convert_to_hevc:
            cmd.extend(["-c:v", "libx265", "-crf", "23", "-preset", "medium"])
        else:
            cmd.extend(["-c:v", "copy"])
        
        if burn_subs:
            cmd.extend(["-vf", "subtitles=" + input_path])
        
        cmd.extend(["-c:a", "copy", output_path])
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path
        except subprocess.CalledProcessError:
            logger.error("Post-processing failed")
            return input_path