# Multi-stage/Slim production Dockerfile optimized for Render Free (512MB RAM)
FROM python:3.11-slim

# Prevent Python from writing .pyc files, enable unbuffered logging,
# and cap glibc malloc arenas to 2 to prevent multithreaded memory fragmentation on 512MB RAM
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000 \
    HOST=0.0.0.0

# Install system dependencies:
# - ffmpeg: media merging and audio conversion
# - nodejs: REQUIRED by yt-dlp 2026+ (yt-dlp-ejs) to solve YouTube n-sig / signatureCipher challenges
# - curl & ca-certificates: container healthchecks and HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user for container security
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Set working directory
WORKDIR /app

# Install Python requirements (skipping duplicate 80MB imageio-ffmpeg wheel since system ffmpeg is installed)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    grep -vE '^(imageio-ffmpeg|pytest)' requirements.txt > requirements.prod.txt && \
    pip install --no-cache-dir -r requirements.prod.txt && \
    rm -f requirements.prod.txt

# Copy source code and static frontend
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create downloads folder and assign ownership to non-root user
RUN mkdir -p /app/downloads && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port (can be overridden by $PORT on Render/Railway/Fly.io)
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Launch production server with single worker and tuned keep-alive for 512MB RAM
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 15"]
