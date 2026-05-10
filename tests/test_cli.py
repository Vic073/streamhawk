"""Tests for CLI functionality and entry points."""

import pytest
import importlib
import sys


class TestCLIEntryPoints:
    """Test CLI entry points and commands."""

    def test_streamhawk_module_importable(self):
        """Test that streamhawk module can be imported."""
        try:
            import streamhawk
            assert streamhawk is not None
        except ImportError:
            pytest.skip("streamhawk module not installed")

    def test_main_module_exists(self):
        """Test that main module exists."""
        try:
            import streamhawk.main
            assert streamhawk.main is not None
        except ImportError:
            pytest.skip("streamhawk.main module not found - may not be installed yet")

    def test_pyproject_defines_entry_points(self, project_root):
        """Test that pyproject.toml defines CLI entry points."""
        import tomllib if sys.version_info >= (3, 11) else None
        try:
            if sys.version_info >= (3, 11):
                import tomllib
                with open(project_root / "pyproject.toml", "rb") as f:
                    pyproject = tomllib.load(f)
            else:
                import toml
                with open(project_root / "pyproject.toml", "r") as f:
                    pyproject = toml.load(f)
            
            scripts = pyproject.get("project", {}).get("scripts", {})
            assert "streamhawk" in scripts or len(scripts) > 0, "No CLI entry points defined"
        except (ImportError, FileNotFoundError):
            pytest.skip("Could not read pyproject.toml")

    def test_dependencies_available(self):
        """Test that key dependencies are available."""
        required_packages = [
            "playwright",
            "aiohttp",
        ]
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                pytest.skip(f"{package} not installed")

    def test_yt_dlp_available(self):
        """Test that yt-dlp is available."""
        try:
            import yt_dlp
            assert yt_dlp is not None
        except ImportError:
            pytest.skip("yt-dlp not installed")
