"""
Command-line interface and interactive prompts.
"""
import sys
from typing import Optional, List
from pathlib import Path

from .config import Config
from .extractor import StreamInfo
from .imdb import MovieMetadata
from .downloader import DownloadProgress
from .utils import logger, extract_imdb_id, HistoryManager


def print_banner():
    """Print application banner."""
    print("=" * 60)
    print("  Project Horizon - HLS Stream Extractor v2.0")
    print("=" * 60)
    print()


def get_imdb_input() -> Optional[str]:
    """Get and validate IMDb ID or URL from user."""
    user_input = input("[?] Paste IMDb URL or ID (e.g., tt0816692): ").strip()
    
    if not user_input:
        print("[-] No input provided")
        return None
    
    imdb_id = extract_imdb_id(user_input)
    if not imdb_id:
        print("[-] Invalid IMDb URL or ID format")
        print("    Expected: tt0816692 or https://www.imdb.com/title/tt0816692/")
        return None
    
    return imdb_id


def confirm_prompt(message: str, default: bool = True) -> bool:
    """Get yes/no confirmation from user."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = input(f"[?] {message}{suffix}").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']


def get_output_filename(metadata: MovieMetadata = None, 
                        default_template: str = "%(title)s (%(year)s).mp4") -> Optional[str]:
    """Get output filename from user with metadata suggestion."""
    if metadata and metadata.title:
        suggested = metadata.format_filename(default_template)
        suggested = suggested.replace('.%(ext)s', '.mp4')
        print(f"[*] Suggested filename: {suggested}")
        
        use_suggested = confirm_prompt("Use suggested filename?", default=True)
        if use_suggested:
            return suggested
    
    custom = input("[?] Enter custom filename (or press Enter to auto-generate): ").strip()
    
    if custom:
        if not any(custom.endswith(ext) for ext in ['.mp4', '.mkv', '.ts']):
            custom += '.mp4'
        return custom
    
    return None


def select_quality(available_qualities: List[str], default: str = "best") -> str:
    """Let user select quality."""
    if not available_qualities:
        return default
    
    print("\n[*] Available qualities:")
    for i, quality in enumerate(available_qualities, 1):
        marker = " (default)" if quality == default else ""
        print(f"    {i}. {quality}{marker}")
    
    choice = input(f"\n[?] Select quality (1-{len(available_qualities)}, or press Enter for {default}): ").strip()
    
    if not choice:
        return default
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(available_qualities):
            return available_qualities[idx]
    except ValueError:
        pass
    
    return default


def print_progress(progress: DownloadProgress):
    """Print download progress."""
    if progress.status == "complete":
        print("\n[+] Download complete!")
        return
    
    if progress.status == "error":
        print("\n[-] Download failed!")
        return
    
    bar_length = 30
    filled = int(bar_length * progress.percent / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    status_line = f"\r    [{bar}] {progress.percent:.1f}%"
    
    if progress.speed:
        status_line += f" | {progress.speed}"
    
    if progress.eta:
        status_line += f" | ETA: {progress.eta}"
    
    print(status_line, end='', flush=True)


def print_stream_info(stream_info: StreamInfo, metadata: MovieMetadata = None):
    """Print stream information."""
    print("\n[*] Stream captured:")
    print(f"    URL: {stream_info.url[:80]}...")
    print(f"    Type: {'Master playlist' if stream_info.is_master else 'Media playlist'}")
    
    if stream_info.resolution:
        print(f"    Resolution: {stream_info.resolution}")
    
    if metadata:
        print(f"\n[*] Movie info:")
        print(f"    Title: {metadata.title}")
        if metadata.year:
            print(f"    Year: {metadata.year}")
        if metadata.rating:
            print(f"    Rating: {metadata.rating}/10")
        if metadata.plot:
            print(f"    Plot: {metadata.plot[:100]}...")


def print_history(history: HistoryManager, limit: int = 5):
    """Print recent download history."""
    recent = history.get_recent(limit)
    
    if not recent:
        return
    
    print("\n[*] Recent downloads:")
    for entry in recent:
        status_icon = "✓" if entry['status'] == 'success' else "✗"
        print(f"    {status_icon} {entry['imdb_id']} - {entry['title']} ({entry['status']})")


def interactive_setup(config: Config) -> Config:
    """Interactive configuration setup."""
    print("\n[*] Configuration Setup")
    print("-" * 40)
    
    # Headless mode
    config.headless = confirm_prompt("Run browser headless by default?", config.headless)
    
    # Download directory
    print(f"\n[*] Current download directory: {config.download_dir}")
    change_dir = confirm_prompt("Change download directory?", False)
    if change_dir:
        new_dir = input("[?] Enter new download path: ").strip()
        if new_dir:
            config.download_dir = new_dir
            Path(config.download_dir).mkdir(parents=True, exist_ok=True)
    
    # Default quality
    print("\n[*] Default quality options:")
    qualities = ['best', '1080p', '720p', '480p', '360p']
    for i, q in enumerate(qualities, 1):
        marker = " (current)" if q == config.default_quality else ""
        print(f"    {i}. {q}{marker}")
    
    q_choice = input(f"[?] Select default quality (1-{len(qualities)}): ").strip()
    try:
        q_idx = int(q_choice) - 1
        if 0 <= q_idx < len(qualities):
            config.default_quality = qualities[q_idx]
    except ValueError:
        pass
    
    # Proxy
    use_proxy = confirm_prompt("Use proxy?", config.proxy is not None)
    if use_proxy:
        config.proxy = input("[?] Enter proxy (e.g., http://host:port): ").strip()
    
    # Notifications
    config.desktop_notifications = confirm_prompt("Enable desktop notifications?", config.desktop_notifications)
    
    # Save config
    save = confirm_prompt("Save this configuration?", True)
    if save:
        config.save()
        print(f"[+] Configuration saved to config.json")
    
    return config


def parse_args():
    """Parse command-line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Project Horizon - HLS Stream Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Interactive mode
  %(prog)s --imdb tt0816692          # Direct IMDb ID
  %(prog)s --config                  # Configuration setup
  %(prog)s --batch movies.txt        # Batch processing
        """
    )
    
    parser.add_argument("--imdb", "-i", help="IMDb ID or URL")
    parser.add_argument("--headful", action="store_true", help="Run browser in headful mode")
    parser.add_argument("--output", "-o", help="Output filename")
    parser.add_argument("--quality", "-q", choices=['best', '1080p', '720p', '480p', '360p'],
                       help="Preferred quality")
    parser.add_argument("--proxy", "-p", help="Proxy URL (http://host:port)")
    parser.add_argument("--batch", "-b", help="Batch file with IMDb IDs (one per line)")
    parser.add_argument("--config", action="store_true", help="Run configuration setup")
    parser.add_argument("--history", action="store_true", help="Show download history")
    parser.add_argument("--preview", action="store_true", help="Preview stream before download")
    parser.add_argument("--no-download", action="store_true", help="Extract URL only, don't download")
    
    return parser.parse_args()


def handle_batch_download(batch_file: str, config: Config):
    """Process batch file with multiple IMDb IDs."""
    path = Path(batch_file)
    
    if not path.exists():
        print(f"[-] Batch file not found: {batch_file}")
        return
    
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    imdb_ids = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        imdb_id = extract_imdb_id(line)
        if imdb_id:
            imdb_ids.append(imdb_id)
    
    print(f"[*] Found {len(imdb_ids)} movies in batch file")
    
    for i, imdb_id in enumerate(imdb_ids, 1):
        print(f"\n{'='*60}")
        print(f"[*] Processing {i}/{len(imdb_ids)}: {imdb_id}")
        print(f"{'='*60}")
        
        # Process each movie
        # Note: Would need to call main processing function here
        # For now, just print the IDs
        print(f"[+] Would process: {imdb_id}")
        
        if i < len(imdb_ids):
            cont = confirm_prompt("Continue to next movie?", True)
            if not cont:
                print("[*] Batch processing cancelled")
                break