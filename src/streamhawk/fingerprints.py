"""
Browser fingerprint randomization and anti-detection.
"""
import random
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BrowserFingerprint:
    """Browser fingerprint data."""
    user_agent: str
    screen_resolution: tuple
    color_depth: int
    pixel_ratio: float
    timezone: str
    languages: list
    platform: str
    hardware_concurrency: int
    device_memory: int
    max_touch_points: int
    webdriver: bool = False


class FingerprintManager:
    """Manages browser fingerprint randomization."""
    
    # Realistic user agents
    CHROME_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    
    EDGE_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    ]
    
    # Common screen resolutions
    RESOLUTIONS = [
        (1920, 1080),
        (1920, 1200),
        (2560, 1440),
        (2560, 1600),
        (1366, 768),
        (1440, 900),
        (1680, 1050),
        (3840, 2160),
    ]
    
    # Timezones
    TIMEZONES = [
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Asia/Tokyo",
        "Asia/Shanghai",
        "Australia/Sydney",
    ]
    
    def __init__(self, rotate: bool = False):
        self.rotate = rotate
        self.current_fingerprint: Optional[BrowserFingerprint] = None
    
    def generate_fingerprint(self, browser_type: str = 'chrome') -> BrowserFingerprint:
        """Generate a randomized browser fingerprint."""
        
        # Select user agent
        if browser_type == 'chrome':
            user_agent = random.choice(self.CHROME_UAS)
        elif browser_type == 'edge':
            user_agent = random.choice(self.EDGE_UAS)
        else:
            user_agent = random.choice(self.CHROME_UAS)
        
        # Select resolution
        width, height = random.choice(self.RESOLUTIONS)
        
        # Determine platform from user agent
        if "Windows" in user_agent:
            platform = "Win32"
        elif "Macintosh" in user_agent:
            platform = "MacIntel"
        elif "Linux" in user_agent:
            platform = "Linux x86_64"
        else:
            platform = "Win32"
        
        fingerprint = BrowserFingerprint(
            user_agent=user_agent,
            screen_resolution=(width, height),
            color_depth=24,
            pixel_ratio=random.choice([1.0, 1.25, 1.5, 2.0]),
            timezone=random.choice(self.TIMEZONES),
            languages=['en-US', 'en'],
            platform=platform,
            hardware_concurrency=random.choice([2, 4, 6, 8, 12, 16]),
            device_memory=random.choice([4, 8, 16, 32]),
            max_touch_points=0,
            webdriver=False
        )
        
        self.current_fingerprint = fingerprint
        return fingerprint
    
    def get_stealth_script(self, fingerprint: BrowserFingerprint = None) -> str:
        """Generate JavaScript to apply fingerprint."""
        if not fingerprint:
            fingerprint = self.current_fingerprint or self.generate_fingerprint()
        
        width, height = fingerprint.screen_resolution
        
        script = f"""
        // Fingerprint randomization
        Object.defineProperty(navigator, 'userAgent', {{
            get: () => "{fingerprint.user_agent}"
        }});
        
        Object.defineProperty(navigator, 'platform', {{
            get: () => "{fingerprint.platform}"
        }});
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {fingerprint.hardware_concurrency}
        }});
        
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {fingerprint.device_memory}
        }});
        
        Object.defineProperty(navigator, 'language', {{
            get: () => "{fingerprint.languages[0]}"
        }});
        
        Object.defineProperty(navigator, 'languages', {{
            get: () => {str(fingerprint.languages)}
        }});
        
        Object.defineProperty(navigator, 'maxTouchPoints', {{
            get: () => {fingerprint.max_touch_points}
        }});
        
        // Screen properties
        Object.defineProperty(screen, 'width', {{
            get: () => {width}
        }});
        
        Object.defineProperty(screen, 'height', {{
            get: () => {height}
        }});
        
        Object.defineProperty(screen, 'availWidth', {{
            get: () => {width}
        }});
        
        Object.defineProperty(screen, 'availHeight', {{
            get: () => {height - 40}
        }});
        
        Object.defineProperty(screen, 'colorDepth', {{
            get: () => {fingerprint.color_depth}
        }});
        
        Object.defineProperty(screen, 'pixelDepth', {{
            get: () => {fingerprint.color_depth}
        }});
        
        // Device pixel ratio
        Object.defineProperty(window, 'devicePixelRatio', {{
            get: () => {fingerprint.pixel_ratio}
        }});
        
        // Prevent detection of automation
        delete navigator.__proto__.webdriver;
        """
        
        return script
    
    def get_context_options(self, fingerprint: BrowserFingerprint = None) -> Dict[str, Any]:
        """Get Playwright context options for fingerprint."""
        if not fingerprint:
            fingerprint = self.current_fingerprint or self.generate_fingerprint()
        
        width, height = fingerprint.screen_resolution
        
        return {
            'user_agent': fingerprint.user_agent,
            'viewport': {'width': width, 'height': height},
            'device_scale_factor': fingerprint.pixel_ratio,
            'locale': fingerprint.languages[0],
            'timezone_id': fingerprint.timezone,
            'permissions': ['geolocation', 'notifications'],
        }


class StealthHelper:
    """Helper class for additional stealth measures."""
    
    @staticmethod
    def get_canvas_noise_script() -> str:
        """Get script to add slight noise to canvas operations."""
        return """
        // Slight canvas noise to prevent fingerprinting
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
            const imageData = originalGetImageData.call(this, x, y, w, h);
            
            // Add imperceptible noise
            for (let i = 0; i < imageData.data.length; i += 4) {
                const noise = (Math.random() - 0.5) * 2;
                imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
                imageData.data[i + 1] = Math.max(0, Math.min(255, imageData.data[i + 1] + noise));
                imageData.data[i + 2] = Math.max(0, Math.min(255, imageData.data[i + 2] + noise));
            }
            
            return imageData;
        };
        """
    
    @staticmethod
    def get_webrtc_hide_script() -> str:
        """Get script to hide WebRTC internal IPs."""
        return """
        // Override WebRTC to prevent internal IP leak
        const originalRTCPeerConnection = window.RTCPeerConnection;
        window.RTCPeerConnection = function(...args) {
            const pc = new originalRTCPeerConnection(...args);
            
            const originalCreateOffer = pc.createOffer.bind(pc);
            pc.createOffer = function() {
                return originalCreateOffer().then(offer => {
                    if (offer.sdp) {
                        offer.sdp = offer.sdp.replace(/a=candidate:.*\r\n/g, '');
                    }
                    return offer;
                });
            };
            
            return pc;
        };
        """
    
    @staticmethod
    def get_font_spoofing_script() -> str:
        """Get script to spoof font detection."""
        return """
        // Common fonts to report
        const fonts = [
            'Arial', 'Arial Black', 'Arial Narrow', 'Book Antiqua',
            'Bookman Old Style', 'Calibri', 'Cambria', 'Century',
            'Century Gothic', 'Comic Sans MS', 'Consolas', 'Courier',
            'Courier New', 'Garamond', 'Georgia', 'Impact', 'Lucida Console',
            'Lucida Sans Unicode', 'Microsoft Sans Serif', 'Monotype Corsiva',
            'MS Gothic', 'MS PGothic', 'MS Reference Sans Serif', 'MS Serif',
            'Palatino Linotype', 'Segoe Print', 'Segoe Script', 'Segoe UI',
            'Tahoma', 'Times', 'Times New Roman', 'Trebuchet MS',
            'Verdana', 'Webdings', 'Wingdings'
        ];
        
        // Override font detection
        const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
        CanvasRenderingContext2D.prototype.measureText = function(text) {
            // Add slight randomization to measurements
            const result = originalMeasureText.call(this, text);
            const randomFactor = 1 + (Math.random() - 0.5) * 0.001;
            result.width *= randomFactor;
            return result;
        };
        """
    
    @staticmethod
    def get_plugins_spoofing_script() -> str:
        """Get script to spoof navigator.plugins."""
        return """
        // Create fake plugins list
        const fakePlugins = [
            {
                name: "Chrome PDF Plugin",
                filename: "internal-pdf-viewer",
                description: "Portable Document Format",
                version: "undefined",
                length: 1,
                item: function() { return this; },
                namedItem: function() { return this; }
            },
            {
                name: "Native Client",
                filename: "internal-nacl-plugin",
                description: "Native Client module",
                version: "undefined",
                length: 2,
                item: function() { return this; },
                namedItem: function() { return this; }
            }
        ];
        
        Object.defineProperty(navigator, 'plugins', {
            get: () => fakePlugins,
            enumerable: true,
            configurable: true
        });
        
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => [
                {type: "application/pdf", suffixes: "pdf", description: ""},
                {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"}
            ],
            enumerable: true,
            configurable: true
        });
        """


def get_full_stealth_script(fingerprint_manager: FingerprintManager = None) -> str:
    """Get complete stealth script combining all anti-detection measures."""
    if not fingerprint_manager:
        fingerprint_manager = FingerprintManager()
    
    fingerprint = fingerprint_manager.generate_fingerprint()
    
    parts = [
        fingerprint_manager.get_stealth_script(fingerprint),
        StealthHelper.get_canvas_noise_script(),
        StealthHelper.get_webrtc_hide_script(),
        StealthHelper.get_font_spoofing_script(),
        StealthHelper.get_plugins_spoofing_script(),
    ]
    
    return "\n\n".join(parts)
