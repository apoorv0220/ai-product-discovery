# AI Product Discovery Suite - Recommendation Service Dockerfile
#
# @category    Infrastructure  
# @author      AI Product Discovery Team
# @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
# @license     https://opensource.org/licenses/MIT MIT License

FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install base requirements first (for better caching)
COPY requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt

# Copy service code
COPY recommendation-service/ ./recommendation-service/
COPY shared/ ./shared/

# Create non-root user
RUN useradd --create-home --shell /bin/bash discovery && \
    chown -R discovery:discovery /app
USER discovery

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run application
CMD ["python", "recommendation-service/main.py"]