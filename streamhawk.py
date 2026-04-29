import asyncio
import subprocess
import sys
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Anti-detection init script to bypass disable-devtool and other common protections
ANTI_DETECTION_SCRIPT = """
// Mask WebDriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Mask Chrome runtime
if (window.chrome) {
    Object.defineProperty(window, 'chrome', {
        get: () => ({
            runtime: {},
            loadTimes: () => ({}),
            csi: () => ({}),
            app: {}
        })
    });
}

// Override permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Prevent devtool detection
setInterval(() => {
    const before = performance.now();
    debugger;
    const after = performance.now();
    if (after - before > 100) {
        // DevTools detected, do nothing (neutralize)
    }
}, 1000);

// Override console.clear
try {
    const originalClear = console.clear;
    console.clear = () => {};
} catch (e) {}
"""

REAL_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def extract_imdb_id(url_or_id: str) -> str:
    """Extract IMDb ID from URL or validate direct ID input."""
    url_or_id = url_or_id.strip()
    
    # Direct IMDb ID pattern
    if re.match(r"^tt\d+$", url_or_id):
        return url_or_id
    
    # Extract from IMDb URL patterns
    patterns = [
        r"imdb\.com/title/(tt\d+)",
        r"imdb\.com/Title\?(tt\d+)",
        r"/title/(tt\d+)",
        r"^(tt\d+)$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None


def build_target_url(imdb_id: str) -> str:
    """Construct the target streaming URL from IMDb ID."""
    return f"https://vidsrc.to/embed/movie/{imdb_id}"


async def intercept_hls_stream(target_url: str, headless: bool = True, timeout_seconds: int = 45):
    """
    Navigate to target URL and intercept .m3u8 stream manifest.
    Returns (m3u8_url, headers, error_message)
    """
    m3u8_url = None
    captured_headers = {}
    error_message = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-web-security',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
            ]
        )
        
        context = await browser.new_context(
            user_agent=REAL_USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True,
            bypass_csp=True,
        )
        
        page = await context.new_page()
        
        # Inject anti-detection script
        await page.add_init_script(ANTI_DETECTION_SCRIPT)
        
        # Pop-up Management: Auto-close popups (ad triggers)
        async def handle_popup(popup):
            print("    [*] Pop-up detected and closed")
            await popup.close()
        page.on("popup", handle_popup)
        
        # Network Sniffing: Intercept requests for .m3u8
        async def on_request(request):
            nonlocal m3u8_url, captured_headers
            if m3u8_url:
                return
            
            url = request.url
            if ".m3u8" in url and "ads" not in url.lower() and "advert" not in url.lower():
                print(f"    [+] HLS manifest captured!")
                m3u8_url = url
                headers = await request.all_headers()
                captured_headers = {
                    "Referer": target_url,
                    "User-Agent": headers.get("user-agent", REAL_USER_AGENT)
                }
        
        page.on("request", on_request)
        
        # Handle dialog auto-dismiss
        page.on("dialog", lambda dialog: dialog.dismiss())
        
        try:
            print(f"    [*] Navigating to target...")
            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            
            # Check for 404 or error pages
            if response:
                if response.status == 404:
                    error_message = "Movie not found in database (404)"
                    return None, None, error_message
                elif response.status >= 400:
                    error_message = f"Server error: HTTP {response.status}"
                    return None, None, error_message
            
            # Wait for potential redirects and dynamic content
            await asyncio.sleep(2)
            
            # Check page content for common error indicators
            page_content = await page.content()
            error_indicators = ["404", "not found", "error", "movie not available"]
            if any(indicator in page_content.lower() for indicator in error_indicators):
                # Might be a soft 404
                pass
            
            # Poll for m3u8 capture with timeout
            elapsed = 0
            while elapsed < timeout_seconds:
                if m3u8_url:
                    break
                await asyncio.sleep(1)
                elapsed += 1
                
            if not m3u8_url and elapsed >= timeout_seconds:
                error_message = "Timeout: No HLS stream detected"
                
        except PlaywrightTimeoutError:
            error_message = "Page load timeout"
        except Exception as e:
            error_message = f"Navigation error: {str(e)}"
        finally:
            await browser.close()
    
    return m3u8_url, captured_headers, error_message


def run_ytdlp(m3u8_url: str, headers: dict, output_name: str = None) -> bool:
    """
    Invoke yt-dlp with captured headers.
    Returns True if successful, False otherwise.
    """
    referer = headers.get("Referer", "")
    user_agent = headers.get("User-Agent", REAL_USER_AGENT)
    
    cmd = [
        "yt-dlp",
        "--referer", referer,
        "--user-agent", user_agent,
        "--add-header", f"Referer:{referer}",
        "--add-header", f"Origin:{referer.rsplit('/', 1)[0]}",
        "--no-warnings",
        "--progress",
        "--newline",
    ]
    
    # Add output filename if provided
    if output_name:
        cmd.extend(["-o", output_name])
    
    # Add HLS specific options
    cmd.extend([
        "--hls-use-mpegts",
        "--retries", "10",
        "--fragment-retries", "10",
    ])
    
    cmd.append(m3u8_url)
    
    print(f"\n[*] Executing: yt-dlp --referer \"...\" --user-agent \"...\" [HLS URL]")
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[-] yt-dlp failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print("[-] yt-dlp not found. Install: pip install yt-dlp")
        return False


async def main():
    print("=" * 60)
    print("  Project Horizon - HLS Stream Extractor")
    print("=" * 60)
    print()
    
    # Interactive input
    user_input = input("[?] Paste IMDb URL or ID (e.g., tt0816692 or imdb.com/title/tt0816692): ").strip()
    
    if not user_input:
        print("[-] No input provided")
        sys.exit(1)
    
    # Extract IMDb ID
    imdb_id = extract_imdb_id(user_input)
    if not imdb_id:
        print("[-] Invalid IMDb URL or ID format")
        print("    Expected: tt0816692 or https://www.imdb.com/title/tt0816692/")
        sys.exit(1)
    
    print(f"[+] Extracted IMDb ID: {imdb_id}")
    
    # Build target URL
    target_url = build_target_url(imdb_id)
    print(f"[*] Target: {target_url}")
    print()
    
    # Ask for headless mode preference
    headless_input = input("[?] Run browser headless? (Y/n, default: Y): ").strip().lower()
    headless = headless_input not in ["n", "no"]
    
    # Ask for output filename
    output_name = input("[?] Output filename (optional, press Enter to skip): ").strip()
    if output_name and not output_name.endswith(('.mp4', '.mkv', '.ts')):
        output_name += '.mp4'
    
    print()
    print("[*] Starting stream extraction...")
    print("-" * 40)
    
    # Intercept stream
    m3u8_url, headers, error = await intercept_hls_stream(target_url, headless=headless)
    
    print("-" * 40)
    
    if error:
        print(f"[-] Extraction failed: {error}")
        sys.exit(1)
    
    if not m3u8_url:
        print("[-] Failed to capture HLS manifest")
        print("    Possible causes:")
        print("    - Movie not available on the mirror")
        print("    - Anti-bot protection triggered")
        print("    - Stream uses different protocol")
        sys.exit(1)
    
    print(f"[+] Stream URL captured")
    print(f"[*] Headers: Referer={headers.get('Referer', 'N/A')}")
    print()
    
    # Confirm before download
    confirm = input("[?] Start download with yt-dlp? (Y/n): ").strip().lower()
    if confirm in ["n", "no"]:
        print("[*] Cancelled by user")
        print(f"[*] URL: {m3u8_url}")
        sys.exit(0)
    
    # Download
    success = run_ytdlp(m3u8_url, headers, output_name if output_name else None)
    
    if success:
        print()
        print("[+] Download completed successfully")
    else:
        print()
        print("[-] Download failed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user")
        sys.exit(0)
