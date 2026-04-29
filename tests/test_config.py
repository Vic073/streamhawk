"""
Tests for configuration module.
"""
import os
import json
import tempfile
import unittest
from pathlib import Path

from streamhawk.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for Config class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        self.assertTrue(config.headless)
        self.assertEqual(config.browser_timeout, 45)
        self.assertEqual(config.default_quality, "best")
        self.assertTrue(config.auto_resume)
        self.assertEqual(config.max_retries, 3)
    
    def test_config_save_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"
            
            # Create and save config
            config = Config(
                headless=False,
                browser_timeout=60,
                default_quality="720p"
            )
            config.save(str(config_path))
            
            # Load config
            loaded = Config.from_file(str(config_path))
            
            self.assertFalse(loaded.headless)
            self.assertEqual(loaded.browser_timeout, 60)
            self.assertEqual(loaded.default_quality, "720p")
    
    def test_proxy_selection(self):
        """Test proxy selection logic."""
        config = Config(
            proxy="http://proxy1:8080",
            use_rotating_proxies=True,
            proxy_list=["http://proxy1:8080", "http://proxy2:8080"]
        )
        
        # Should return from proxy_list when rotating
        proxy = config.get_proxy()
        self.assertIn(proxy, config.proxy_list)


if __name__ == "__main__":
    unittest.main()
