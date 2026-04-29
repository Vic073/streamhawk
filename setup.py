"""
Setup script for StreamHawk - Project Horizon HLS Stream Extractor
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="streamhawk",
    version="2.0.0",
    author="Project Horizon",
    description="Automated HLS Stream Extractor with yt-dlp integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/streamhawk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "streamhawk=streamhawk.main:main",
            "shawk=streamhawk.main:main",
        ],
    },
    keywords="hls, m3u8, video, download, yt-dlp, imdb, streaming",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/streamhawk/issues",
        "Source": "https://github.com/yourusername/streamhawk",
    },
)
