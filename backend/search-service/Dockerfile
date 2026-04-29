# AI Product Discovery Suite - Search Service
ARG BASE_IMAGE=discovery-base:latest
FROM ${BASE_IMAGE}

ENV SERVICE_NAME=search

# Copy service code
COPY search-service/ ./search-service/

# Copy alembic configuration for migrations
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Ensure ownership (user already exists from base image)
USER root
RUN chown -R discovery:discovery /app
USER discovery

# Expose port
EXPOSE 7099

# Health check removed - using docker-compose healthcheck instead

# Run application
CMD ["uvicorn", "search-service.main:app", "--host", "0.0.0.0", "--port", "7099"]