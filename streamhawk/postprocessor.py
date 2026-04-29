"""
Video post-processing with ffmpeg.
"""
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ProcessingOptions:
    """Options for video post-processing."""
    # Video encoding
    codec: str = 'copy'  # 'copy', 'libx264', 'libx265', 'libvpx', etc.
    crf: int = 23  # Quality (lower is better, 18-28 typical)
    preset: str = 'medium'  # 'ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'
    
    # Resolution
    resolution: Optional[str] = None  # e.g., '1920x1080', '1280x720'
    
    # Audio
    audio_codec: str = 'copy'  # 'copy', 'aac', 'mp3', 'opus'
    audio_bitrate: str = '128k'
    
    # Filters
    deinterlace: bool = False
    denoise: bool = False
    normalize_audio: bool = False
    
    # Output
    output_format: str = 'mp4'  # 'mp4', 'mkv', 'webm'
    
    # Hardware acceleration
    hwaccel: Optional[str] = None  # 'cuda', 'vaapi', 'qsv', 'videotoolbox'


class PostProcessor:
    """Video post-processing using ffmpeg."""
    
    PRESETS = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 
               'medium', 'slow', 'slower', 'veryslow']
    
    VIDEO_CODECS = {
        'copy': 'copy',
        'h264': 'libx264',
        'x264': 'libx264',
        'h265': 'libx265',
        'x265': 'libx265',
        'hevc': 'libx265',
        'vp9': 'libvpx-vp9',
        'av1': 'libaom-av1'
    }
    
    AUDIO_CODECS = {
        'copy': 'copy',
        'aac': 'aac',
        'mp3': 'libmp3lame',
        'opus': 'libopus',
        'flac': 'flac'
    }
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is installed."""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("ffmpeg not found. Install ffmpeg to use post-processing.")
    
    def process(self, input_path: str, options: ProcessingOptions = None,
                output_path: str = None) -> Optional[str]:
        """
        Process video with given options.
        
        Returns:
            Path to processed video
        """
        if not options:
            options = ProcessingOptions()
        
        if not output_path:
            input_file = Path(input_path)
            suffix = f"_processed.{options.output_format}"
            output_path = str(self.output_dir / (input_file.stem + suffix))
        
        cmd = self._build_command(input_path, options, output_path)
        
        try:
            print(f"[*] Post-processing: {Path(input_path).name}")
            subprocess.run(cmd, check=True, capture_output=True)
            
            if Path(output_path).exists():
                # Get file sizes for comparison
                input_size = Path(input_path).stat().st_size
                output_size = Path(output_path).stat().st_size
                
                print(f"[+] Processing complete: {output_path}")
                print(f"    Size: {self._format_size(input_size)} → {self._format_size(output_size)}")
                
                return output_path
            
        except subprocess.CalledProcessError as e:
            print(f"[-] Processing failed: {e}")
            return None
        
        return None
    
    def _build_command(self, input_path: str, options: ProcessingOptions,
                       output_path: str) -> List[str]:
        """Build ffmpeg command."""
        cmd = ['ffmpeg', '-i', input_path, '-y']
        
        # Hardware acceleration
        if options.hwaccel:
            cmd.extend(['-hwaccel', options.hwaccel])
        
        # Video codec
        video_codec = self.VIDEO_CODECS.get(options.codec, options.codec)
        cmd.extend(['-c:v', video_codec])
        
        if video_codec != 'copy':
            cmd.extend(['-crf', str(options.crf)])
            cmd.extend(['-preset', options.preset])
            
            # Pixel format for HEVC
            if video_codec == 'libx265':
                cmd.extend(['-pix_fmt', 'yuv420p'])
                cmd.extend(['-tag:v', 'hvc1'])  # For Apple compatibility
        
        # Resolution
        if options.resolution:
            cmd.extend(['-vf', f'scale={options.resolution}'])
        
        # Deinterlace
        if options.deinterlace:
            cmd.extend(['-vf', 'yadif'])
        
        # Denoise
        if options.denoise:
            cmd.extend(['-vf', 'hqdn3d'])
        
        # Audio
        audio_codec = self.AUDIO_CODECS.get(options.audio_codec, options.audio_codec)
        cmd.extend(['-c:a', audio_codec])
        
        if audio_codec != 'copy':
            cmd.extend(['-b:a', options.audio_bitrate])
        
        # Audio normalization
        if options.normalize_audio:
            cmd.extend(['-af', 'loudnorm=I=-16:TP=-1.5:LRA=11'])
        
        # Output
        cmd.append(output_path)
        
        return cmd
    
    def convert_to_hevc(self, input_path: str, crf: int = 28,
                       output_path: str = None) -> Optional[str]:
        """
        Convert video to HEVC/H.265 for better compression.
        
        Returns:
            Path to converted video
        """
        options = ProcessingOptions(
            codec='libx265',
            crf=crf,
            preset='slow',
            output_format='mp4'
        )
        
        return self.process(input_path, options, output_path)
    
    def compress_for_web(self, input_path: str, 
                        max_width: int = 1280,
                        output_path: str = None) -> Optional[str]:
        """
        Compress video for web streaming.
        
        Returns:
            Path to compressed video
        """
        options = ProcessingOptions(
            codec='libx264',
            crf=23,
            preset='medium',
            resolution=f'{max_width}:-2',  # Maintain aspect ratio
            audio_codec='aac',
            audio_bitrate='96k',
            output_format='mp4'
        )
        
        return self.process(input_path, options, output_path)
    
    def extract_thumbnail(self, video_path: str, time: str = '00:00:01',
                         output_path: str = None) -> Optional[str]:
        """
        Extract thumbnail from video at specified time.
        
        Args:
            video_path: Path to video file
            time: Timestamp (HH:MM:SS or seconds)
            output_path: Output thumbnail path
            
        Returns:
            Path to thumbnail image
        """
        if not output_path:
            base = Path(video_path).stem
            output_path = str(self.output_dir / f"{base}_thumb.jpg")
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', time,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path if Path(output_path).exists() else None
        except subprocess.CalledProcessError:
            return None
    
    def extract_audio(self, video_path: str, format: str = 'mp3',
                     output_path: str = None) -> Optional[str]:
        """
        Extract audio track from video.
        
        Returns:
            Path to audio file
        """
        if not output_path:
            base = Path(video_path).stem
            output_path = str(self.output_dir / f"{base}_audio.{format}")
        
        audio_codecs = {
            'mp3': 'libmp3lame',
            'aac': 'aac',
            'opus': 'libopus',
            'flac': 'flac',
            'wav': 'pcm_s16le'
        }
        
        codec = audio_codecs.get(format, 'copy')
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-c:a', codec,
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path if Path(output_path).exists() else None
        except subprocess.CalledProcessError:
            return None
    
    def trim(self, video_path: str, start: str, end: str,
            output_path: str = None) -> Optional[str]:
        """
        Trim video to specified time range.
        
        Args:
            start: Start time (HH:MM:SS or seconds)
            end: End time (HH:MM:SS or seconds)
            
        Returns:
            Path to trimmed video
        """
        if not output_path:
            base = Path(video_path).stem
            output_path = str(self.output_dir / f"{base}_trimmed.mp4")
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', start,
            '-to', end,
            '-c', 'copy',  # Stream copy (no re-encode)
            '-y',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return output_path if Path(output_path).exists() else None
        except subprocess.CalledProcessError:
            return None
    
    def get_media_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get media file information using ffprobe.
        
        Returns:
            Dictionary with media information
        """
        import json
        
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            info = {
                'format': data.get('format', {}),
                'streams': []
            }
            
            for stream in data.get('streams', []):
                stream_info = {
                    'type': stream.get('codec_type'),
                    'codec': stream.get('codec_name'),
                    'duration': stream.get('duration'),
                }
                
                if stream.get('codec_type') == 'video':
                    stream_info['width'] = stream.get('width')
                    stream_info['height'] = stream.get('height')
                    stream_info['fps'] = eval(stream.get('r_frame_rate', '0/1'))
                    
                elif stream.get('codec_type') == 'audio':
                    stream_info['channels'] = stream.get('channels')
                    stream_info['sample_rate'] = stream.get('sample_rate')
                
                info['streams'].append(stream_info)
            
            return info
            
        except Exception as e:
            print(f"[-] Failed to get media info: {e}")
            return {}
    
    def verify_integrity(self, video_path: str) -> bool:
        """
        Verify video file integrity.
        
        Returns:
            True if file is valid
        """
        cmd = [
            'ffmpeg',
            '-v', 'error',
            '-i', video_path,
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0 and not result.stderr
        except Exception:
            return False
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
