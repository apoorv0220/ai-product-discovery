# AI Product Discovery Suite - Recommendation Service
ARG BASE_IMAGE=discovery-base:latest
FROM ${BASE_IMAGE}

# Copy service code
COPY recommendation-service/ ./recommendation-service/

# Ensure ownership (user already exists from base image)
USER root
RUN chown -R discovery:discovery /app
USER discovery

# Expose port
EXPOSE 7099

# Health check removed - using docker-compose healthcheck instead

# Run application
CMD ["uvicorn", "recommendation-service.main:app", "--host", "0.0.0.0", "--port", "7099"]