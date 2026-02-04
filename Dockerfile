# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

# Production stage
FROM python:3.11-slim

# OCI Labels for GitHub Container Registry (ghcr.io)
LABEL org.opencontainers.image.source="https://github.com/biker2000on/movie-manager"
LABEL org.opencontainers.image.description="Radarr Horror Filter - CLI tool to scan and delete horror movies from Radarr"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.title="movie-manager"
LABEL org.opencontainers.image.vendor="biker2000on"

# Install bash for entrypoint script
RUN apt-get update && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --uid 1000 appuser

# Set working directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /app/deps /usr/local/lib/python3.11/site-packages/

# Copy ALL Python files (future-proof for new modules)
COPY *.py ./

# Create data directory for persistent storage
RUN mkdir -p /data && chown appuser:appuser /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV KEEP_LIST_PATH=/data/.keep-list.json

# Copy and set entrypoint
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh && chown appuser:appuser /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Health check - verify Python and app are working
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import radarr_horror_filter; print('OK')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--help"]
