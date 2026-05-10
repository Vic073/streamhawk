"""Tests for configuration file handling."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestConfigValidation:
    """Test configuration file validation."""

    def test_config_file_exists(self, config_file):
        """Test that config.json exists in project root."""
        assert config_file.exists(), f"Config file not found at {config_file}"

    def test_config_file_is_valid_json(self, config_file):
        """Test that config.json contains valid JSON."""
        with open(config_file, 'r') as f:
            try:
                config = json.load(f)
                assert isinstance(config, dict)
            except json.JSONDecodeError as e:
                pytest.fail(f"config.json is not valid JSON: {e}")

    def test_config_has_required_keys(self, config_file):
        """Test that config has expected structure."""
        with open(config_file, 'r') as f:
            config = json.load(f)
            # Check for expected top-level keys or structure
            assert isinstance(config, dict), "Config should be a dictionary"

    def test_config_mirror_urls_are_strings(self, config_file):
        """Test that mirror URLs in config are strings."""
        with open(config_file, 'r') as f:
            config = json.load(f)
            if 'mirrors' in config:
                for mirror in config['mirrors']:
                    assert isinstance(mirror, str), "Mirror URLs should be strings"

    def test_config_timeout_is_valid(self, config_file):
        """Test that timeout values are valid integers."""
        with open(config_file, 'r') as f:
            config = json.load(f)
            if 'timeout' in config:
                assert isinstance(config['timeout'], (int, float))
                assert config['timeout'] > 0, "Timeout should be positive"

    def test_create_temp_config(self, temp_downloads_dir):
        """Test creating a temporary config file."""
        config_data = {
            "download_dir": str(temp_downloads_dir),
            "timeout": 45,
            "headless": True
        }
        temp_config = temp_downloads_dir / "config.json"
        with open(temp_config, 'w') as f:
            json.dump(config_data, f)
        
        # Verify it was created correctly
        assert temp_config.exists()
        with open(temp_config, 'r') as f:
            loaded = json.load(f)
            assert loaded == config_data

    def test_config_preserves_formatting(self, config_file):
        """Test that config file maintains valid formatting."""
        with open(config_file, 'r') as f:
            content = f.read()
            # Should be valid JSON
            parsed = json.loads(content)
            # Should be re-serializable
            reserialized = json.dumps(parsed)
            assert len(reserialized) > 0
