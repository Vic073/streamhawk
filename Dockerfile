# StreamHawk - HLS Stream Extractor
# Multi-stage build for smaller final image

FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Production stage
FROM base as production

WORKDIR /app

# Copy pyproject.toml for dependency installation
COPY pyproject.toml .

# Install Python dependencies using modern pyproject.toml
RUN pip install --no-cache-dir -e .

# Install Playwright browsers
RUN playwright install chromium

# Copy application code
COPY src/ ./src/
COPY config.json .
COPY README.md .

# Create downloads directory
RUN mkdir -p /downloads

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STREAMHAWK_DOWNLOAD_DIR=/downloads

# Volume for downloads
VOLUME ["/downloads"]

# Default command - use installed entry point
ENTRYPOINT ["streamhawk"]
CMD ["--help"]

# Development stage
FROM base as development

WORKDIR /app

# Install dev dependencies
RUN pip install pytest pytest-asyncio pytest-cov black ruff bandit safety

# Copy all project files
COPY . .

# Install package in development mode
RUN pip install --no-cache-dir -e ".[dev]"

# Install Playwright browsers
RUN playwright install chromium

# Run tests by default in dev mode
CMD ["pytest", "-v", "--cov=src", "--cov-report=term-missing"]
