"""
Browser automation module with anti-detection features.
"""
from typing import Optional, Dict, Any, Callable
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError


# Enhanced anti-detection script
ANTI_DETECTION_SCRIPT = """
// Mask WebDriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

// Mask Chrome runtime
Object.defineProperty(window, 'chrome', {
    get: () => ({
        runtime: {
            OnInstalledReason: {CHROME_UPDATE: "chrome_update", UPDATE: "update", INSTALL: "install"},
            OnRestartRequiredReason: {APP_UPDATE: "app_update", OS_UPDATE: "os_update", PERIODIC: "periodic"},
            PlatformArch: {ARM: "arm", ARM64: "arm64", MIPS: "mips", MIPS64: "mips64", X86_32: "x86-32", X86_64: "x86-64"},
            PlatformNaclArch: {ARM: "arm", MIPS: "mips", MIPS64: "mips64", X86_32: "x86-32", X86_64: "x86-64"},
            PlatformOs: {ANDROID: "android", CROS: "cros", LINUX: "linux", MAC: "mac", OPENBSD: "openbsd", WIN: "win"},
            RequestUpdateCheckStatus: {NO_UPDATE: "no_update", THROTTLED: "throttled", UPDATE_AVAILABLE: "update_available"}
        },
        loadTimes: () => ({
            commitLoadTime: performance.now(),
            connectionInfo: "h2",
            finishDocumentLoadTime: performance.now(),
            finishLoadTime: performance.now(),
            firstPaintAfterLoadTime: 0,
            firstPaintTime: 0,
            navigationType: "Other",
            npnNegotiatedProtocol: "h2",
            requestTime: performance.now(),
            startLoadTime: performance.now(),
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: true,
            wasNpnNegotiated: true
        }),
        csi: () => ({
            onloadT: Date.now(),
            pageT: Date.now() - performance.timing.navigationStart,
            startE: performance.timing.navigationStart,
            tran: 15
        }),
        app: {
            isInstalled: false,
            InstallState: {DISABLED: "disabled", INSTALLED: "installed", NOT_INSTALLED: "not_installed"},
            RunningState: {CANNOT_RUN: "cannot_run", READY_TO_RUN: "ready_to_run", RUNNING: "running"}
        }
    })
});

// Override permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission, onchange: null }) :
        originalQuery(parameters)
);

// Prevent devtool detection via debugger statement
let devtoolsOpen = false;
const threshold = 160;
setInterval(() => {
    const start = performance.now();
    debugger;
    const end = performance.now();
    if (end - start > threshold) {
        devtoolsOpen = true;
        // Don't react to devtools detection
    }
}, 1000);

// Override console methods to prevent detection
const originalConsoleClear = console.clear;
console.clear = function() {
    // Do nothing - prevent clear
};

// Prevent console size detection
Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth });
Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight });

// Fake WebGL renderer info
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Intel Inc.';
    }
    if (parameter === 37446) {
        return 'Intel Iris OpenGL Engine';
    }
    return getParameter(parameter);
};

// Prevent iframe detection
Object.defineProperty(window, 'IFrameElement', { get: () => undefined });
"""

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

DEFAULT_BROWSER_ARGS = [
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-blink-features=AutomationControlled',
    '--disable-features=IsolateOrigins,site-per-process',
    '--disable-web-security',
    '--disable-features=BlockInsecurePrivateNetworkRequests',
    '--disable-background-networking',
    '--disable-background-timer-throttling',
    '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows',
    '--disable-breakpad',
    '--disable-component-update',
    '--disable-default-apps',
    '--disable-features=TranslateUI',
    '--disable-hang-monitor',
    '--disable-ipc-flooding-protection',
    '--disable-popup-blocking',
    '--disable-prompt-on-repost',
    '--disable-renderer-accessibility',
    '--force-webrtc-ip-handling-policy=default_public_interface_only',
    '--metrics-recording-only',
    '--no-first-run',
    '--safebrowsing-disable-auto-update',
    '--password-store=basic',
    '--use-mock-keychain',
]


class StealthBrowser:
    """Browser manager with stealth capabilities."""
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None,
                 user_agent: Optional[str] = None, timeout: int = 30000):
        self.headless = headless
        self.proxy = proxy
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.timeout = timeout
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
    
    async def start(self) -> 'StealthBrowser':
        """Start browser instance."""
        self._playwright = await async_playwright().start()
        
        browser_args = DEFAULT_BROWSER_ARGS.copy()
        
        # Add proxy if specified
        proxy_config = None
        if self.proxy:
            proxy_config = {'server': self.proxy}
        
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=browser_args,
            proxy=proxy_config
        )
        
        self._context = await self._browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True,
            bypass_csp=True,
            java_script_enabled=True,
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
            permissions=['geolocation']
        )
        
        # Grant additional permissions
        await self._context.grant_permissions(['notifications', 'clipboard-read', 'clipboard-write'])
        
        self._page = await self._context.new_page()
        
        # Inject anti-detection script
        await self._page.add_init_script(ANTI_DETECTION_SCRIPT)
        
        # Setup pop-up handler
        self._page.on("popup", self._handle_popup)
        
        # Setup dialog auto-dismiss
        self._page.on("dialog", lambda dialog: dialog.dismiss())
        
        return self
    
    async def stop(self) -> None:
        """Stop browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    async def _handle_popup(self, popup: Page) -> None:
        """Handle popup windows (ads)."""
        from .utils import logger
        logger.debug("Popup detected and closed")
        await popup.close()
    
    @property
    def page(self) -> Page:
        """Get current page."""
        if not self._page:
            raise RuntimeError("Browser not started")
        return self._page
    
    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> Any:
        """Navigate to URL."""
        return await self._page.goto(url, wait_until=wait_until, timeout=self.timeout)
    
    async def evaluate(self, script: str) -> Any:
        """Execute JavaScript on page."""
        return await self._page.evaluate(script)
    
    def on_request(self, handler: Callable) -> None:
        """Register request handler."""
        self._page.on("request", handler)
    
    def on_response(self, handler: Callable) -> None:
        """Register response handler."""
        self._page.on("response", handler)
    
    async def wait_for_timeout(self, ms: int) -> None:
        """Wait for specified milliseconds."""
        await self._page.wait_for_timeout(ms)
    
    async def content(self) -> str:
        """Get page HTML content."""
        return await self._page.content()


class RequestInterceptor:
    """Intercepts and captures specific requests."""
    
    def __init__(self, target_extensions: list = None, 
                 exclude_patterns: list = None):
        self.target_extensions = target_extensions or ['.m3u8', '.mpd']
        self.exclude_patterns = exclude_patterns or ['ads', 'advert', 'tracking', 'analytics']
        self.captured_urls: Dict[str, Dict[str, Any]] = {}
        self._handlers = []
    
    def create_handler(self, callback: Callable[[str, Dict], None] = None):
        """Create request handler function."""
        async def handler(request):
            url = request.url
            
            # Check if URL matches target extensions
            matched = any(ext in url.lower() for ext in self.target_extensions)
            excluded = any(pat in url.lower() for pat in self.exclude_patterns)
            
            if matched and not excluded:
                headers = await request.all_headers()
                self.captured_urls[url] = {
                    'url': url,
                    'headers': headers,
                    'method': request.method,
                    'post_data': request.post_data
                }
                
                if callback:
                    await callback(url, headers)
        
        return handler
    
    def get_captured(self) -> Dict[str, Dict[str, Any]]:
        """Get all captured URLs."""
        return self.captured_urls
    
    def get_best_stream(self) -> Optional[str]:
        """Get the best quality stream URL."""
        if not self.captured_urls:
            return None
        
        # Prioritize master playlists
        for url, data in self.captured_urls.items():
            if 'master' in url.lower():
                return url
        
        # Return first captured URL
        return list(self.captured_urls.keys())[0]
    
    def clear(self) -> None:
        """Clear captured URLs."""
        self.captured_urls.clear()