# AI Product Discovery Suite - Search Service
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV SERVICE_NAME=search

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
COPY search-service/ ./search-service/
COPY shared/ ./shared/

# Create non-root user
RUN useradd --create-home --shell /bin/bash discovery && \
    chown -R discovery:discovery /app
USER discovery

# Expose port
EXPOSE 7099

# Health check removed - using docker-compose healthcheck instead

# Run application
CMD ["uvicorn", "search-service.main:app", "--host", "0.0.0.0", "--port", "7099"]