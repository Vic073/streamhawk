"""
Main entry point for Project Horizon.
"""
import asyncio
import sys
from pathlib import Path

from streamhawk import Config, StreamExtractor, YTDLPManager, IMDbClient, logger
from streamhawk.cli import (
    print_banner, get_imdb_input, confirm_prompt, get_output_filename,
    select_quality, print_progress, print_stream_info, print_history,
    interactive_setup, parse_args, handle_batch_download
)
from streamhawk.utils import HistoryManager, setup_logger
from streamhawk.notifications import NotificationManager, play_sound


def build_target_url(imdb_id: str) -> str:
    """Construct streaming URL from IMDb ID."""
    return f"https://vidsrc.to/embed/movie/{imdb_id}"


async def process_movie(imdb_id: str, config: Config, 
                        args=None, history: HistoryManager = None) -> bool:
    """
    Process a single movie extraction and download.
    
    Returns:
        True if successful
    """
    # Initialize clients
    imdb_client = IMDbClient()
    extractor = StreamExtractor(config)
    downloader = YTDLPManager(config)
    notifier = NotificationManager(
        desktop=config.desktop_notifications,
        webhook_url=config.webhook_url
    )
    
    target_url = build_target_url(imdb_id)
    
    print(f"\n[+] Extracted IMDb ID: {imdb_id}")
    print(f"[*] Target: {target_url}")
    
    # Fetch metadata
    metadata = None
    if config.fetch_metadata:
        print("[*] Fetching movie metadata...")
        metadata = await imdb_client.fetch_metadata(imdb_id)
        if metadata:
            print(f"[+] Found: {metadata.title} ({metadata.year or 'Unknown'})")
        else:
            metadata = imdb_client.get_suggested_filename(imdb_id)
    
    # Extract stream
    print("\n[*] Starting stream extraction...")
    print("-" * 40)
    
    def progress_callback(msg: str):
        print(f"    [*] {msg}")
    
    stream_info, error = await extractor.extract_with_retry(target_url, progress_callback)
    
    print("-" * 40)
    
    if error:
        print(f"[-] Extraction failed: {error}")
        if history:
            history.add(imdb_id, metadata.title if metadata else imdb_id, 'failed')
        notifier.notify("Extraction Failed", f"{imdb_id}: {error}", "error")
        return False
    
    if not stream_info:
        print("[-] Failed to capture stream")
        if history:
            history.add(imdb_id, metadata.title if metadata else imdb_id, 'failed')
        return False
    
    print_stream_info(stream_info, metadata)
    
    # URL only mode
    if args and args.no_download:
        print(f"\n[*] Stream URL:")
        print(f"    {stream_info.url}")
        print(f"\n[*] Headers:")
        for key, value in stream_info.headers.items():
            print(f"    {key}: {value}")
        return True
    
    # Preview mode
    if args and args.preview:
        print("\n[*] Previewing stream...")
        preview_ok = await extractor.preview_stream(stream_info)
        if not preview_ok:
            print("[-] Preview failed")
    
    # Get output filename
    output_name = None
    if args and args.output:
        output_name = args.output
    else:
        output_name = get_output_filename(metadata, config.output_template)
    
    # Quality selection
    quality = args.quality if (args and args.quality) else config.default_quality
    
    # Confirm download
    if not (args and args.no_download):
        print()
        confirm = confirm_prompt("Start download with yt-dlp?", True)
        if not confirm:
            print("[*] Cancelled by user")
            print(f"[*] URL: {stream_info.url}")
            if history:
                history.add(imdb_id, metadata.title if metadata else imdb_id, 'cancelled', stream_info.url)
            return False
    
    # Download
    print(f"\n[*] Starting download...")
    
    def download_progress(progress):
        print_progress(progress)
    
    success = downloader.download(
        stream_info,
        output_name=output_name,
        quality=quality,
        progress_callback=download_progress
    )
    
    print()
    
    if success:
        print("[+] Download completed successfully")
        if history:
            history.add(imdb_id, metadata.title if metadata else imdb_id, 'success', 
                        stream_info.url, output_name)
        notifier.notify("Download Complete", f"{metadata.title if metadata else imdb_id}", "success")
        play_sound("complete")
        return True
    else:
        print("[-] Download failed")
        if history:
            history.add(imdb_id, metadata.title if metadata else imdb_id, 'failed', stream_info.url)
        notifier.notify("Download Failed", f"{metadata.title if metadata else imdb_id}", "error")
        play_sound("error")
        return False


async def main():
    """Main entry point."""
    try:
        # Parse arguments
        args = parse_args()
        
        # Load or create config
        config = Config.from_file("config.json")
        
        # Setup logging
        global logger
        logger = setup_logger(
            log_dir=config.log_dir,
            level=config.log_level,
            save_to_file=config.save_debug_logs
        )
        
        # Initialize history
        history = HistoryManager() if config.save_history else None
        
        # Handle config setup mode
        if args.config:
            config = interactive_setup(config)
            return
        
        # Handle history display
        if args.history:
            print_history(history)
            return
        
        # Handle batch mode
        if args.batch:
            handle_batch_download(args.batch, config)
            return
        
        # Handle web dashboard mode
        if args.web:
            print(f"[*] Starting web dashboard on http://localhost:{args.port}")
            from .web import run_web
            run_web(host='0.0.0.0', port=args.port, debug=False)
            return
        
        # Print banner for interactive modes
        print_banner()
        
        # Override config with CLI args
        if args.headful:
            config.headless = False
        if args.proxy:
            config.proxy = args.proxy
        
        # Get IMDb ID
        imdb_id = None
        if args.imdb:
            from streamhawk.utils import extract_imdb_id
            imdb_id = extract_imdb_id(args.imdb)
            if not imdb_id:
                print("[-] Invalid IMDb ID provided")
                sys.exit(1)
        else:
            imdb_id = get_imdb_input()
            if not imdb_id:
                sys.exit(1)
        
        # Process movie
        success = await process_movie(imdb_id, config, args, history)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n[*] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error")
        print(f"\n[-] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())