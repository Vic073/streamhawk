"""
Project Horizon - HLS Stream Extractor

A modular tool for extracting HLS streams and downloading via yt-dlp.
"""

__version__ = "2.0.0"
__author__ = "Project Horizon"

from .config import Config
from .extractor import StreamExtractor, StreamInfo
from .downloader import YTDLPManager, DownloadProgress
from .imdb import IMDbClient, MovieMetadata
from .browser import StealthBrowser, RequestInterceptor
from .m3u8_parser import M3U8Parser, M3U8Stream
from .subtitles import SubtitleManager, Subtitle
from .postprocessor import PostProcessor, ProcessingOptions
from .fingerprints import FingerprintManager, StealthHelper
from .notifications import NotificationManager
from .utils import logger, HistoryManager

__all__ = [
    "Config",
    "StreamExtractor",
    "StreamInfo",
    "YTDLPManager",
    "DownloadProgress",
    "IMDbClient",
    "MovieMetadata",
    "StealthBrowser",
    "RequestInterceptor",
    "M3U8Parser",
    "M3U8Stream",
    "SubtitleManager",
    "Subtitle",
    "PostProcessor",
    "ProcessingOptions",
    "FingerprintManager",
    "StealthHelper",
    "NotificationManager",
    "logger",
    "HistoryManager",
]