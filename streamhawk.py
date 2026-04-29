#!/usr/bin/env python3
"""
StreamHawk - Project Horizon HLS Stream Extractor

Entry point script that launches the modular StreamHawk application.
"""
import asyncio
import sys
from pathlib import Path

# Ensure streamhawk package is importable
sys.path.insert(0, str(Path(__file__).parent))

from streamhawk.main import main

if __name__ == "__main__":
    asyncio.run(main())
