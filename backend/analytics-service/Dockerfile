# AI Product Discovery Suite - Analytics Service
FROM python:3.12-slim

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
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY analytics-service/ ./analytics-service/
COPY shared/ ./shared/

# Create non-root user
RUN useradd --create-home --shell /bin/bash discovery && \
    chown -R discovery:discovery /app
USER discovery

# Expose port
EXPOSE 7099

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7099/health || exit 1

# Run application
CMD ["uvicorn", "analytics-service.main:app", "--host", "0.0.0.0", "--port", "7099"]