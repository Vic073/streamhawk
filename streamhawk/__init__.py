"""
Project Horizon - HLS Stream Extractor

A modular tool for extracting HLS streams and downloading via yt-dlp.
"""

__version__ = "2.0.0"
__author__ = "Project Horizon"

from .config import Config
from .extractor import StreamExtractor
from .downloader import YTDLPManager
from .imdb import IMDbClient
from .utils import logger

__all__ = [
    "Config",
    "StreamExtractor", 
    "YTDLPManager",
    "IMDbClient",
    "logger",
]