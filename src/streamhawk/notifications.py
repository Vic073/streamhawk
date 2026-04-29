"""
Notification utilities for desktop and webhook alerts.
"""
import platform
from typing import Optional
from .utils import logger


class NotificationManager:
    """Manages desktop and webhook notifications."""
    
    def __init__(self, desktop: bool = False, webhook_url: Optional[str] = None):
        self.desktop_enabled = desktop
        self.webhook_url = webhook_url
        self.system = platform.system()
    
    def notify(self, title: str, message: str, notification_type: str = "info") -> None:
        """Send notification via all enabled channels."""
        if self.desktop_enabled:
            self._desktop_notify(title, message)
        
        if self.webhook_url:
            self._webhook_notify(title, message, notification_type)
    
    def _desktop_notify(self, title: str, message: str) -> None:
        """Send desktop notification."""
        try:
            if self.system == "Windows":
                self._notify_windows(title, message)
            elif self.system == "Darwin":  # macOS
                self._notify_macos(title, message)
            else:  # Linux
                self._notify_linux(title, message)
        except Exception as e:
            logger.debug(f"Desktop notification failed: {e}")
    
    def _notify_windows(self, title: str, message: str) -> None:
        """Windows toast notification."""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=5, threaded=True)
        except ImportError:
            # Fallback to ctypes
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0)
    
    def _notify_macos(self, title: str, message: str) -> None:
        """macOS notification."""
        import subprocess
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], capture_output=True)
    
    def _notify_linux(self, title: str, message: str) -> None:
        """Linux notification."""
        import subprocess
        subprocess.run(["notify-send", title, message], capture_output=True)
    
    def _webhook_notify(self, title: str, message: str, notification_type: str) -> None:
        """Send webhook notification."""
        import asyncio
        asyncio.create_task(self._async_webhook_send(title, message, notification_type))
    
    async def _async_webhook_send(self, title: str, message: str, notification_type: str) -> None:
        """Async webhook send."""
        try:
            import aiohttp
            
            payload = {
                "title": title,
                "message": message,
                "type": notification_type,
                "source": "StreamHawk"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload, timeout=10):
                    pass
                    
        except Exception as e:
            logger.debug(f"Webhook notification failed: {e}")


def play_sound(sound_type: str = "complete") -> None:
    """Play completion sound."""
    try:
        if platform.system() == "Windows":
            import winsound
            if sound_type == "complete":
                winsound.MessageBeep(winsound.MB_OK)
            elif sound_type == "error":
                winsound.MessageBeep(winsound.MB_ICONHAND)
    except Exception:
        pass
