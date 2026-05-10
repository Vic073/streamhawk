"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def config_file(project_root):
    """Return path to config.json."""
    return project_root / "config.json"


@pytest.fixture
def temp_downloads_dir(tmp_path):
    """Create a temporary downloads directory."""
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    return downloads_dir
