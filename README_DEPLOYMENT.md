# 🚀 AI Product Discovery Suite - Deployment Guide

Welcome to the **AI Product Discovery Suite**! This guide will help you get the entire system up and running quickly.

## 📋 Prerequisites

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Python 3.11+** (for local development)
- **Make** (optional, for convenience commands)
- At least **4GB RAM** and **10GB disk space**

## 🎯 Quick Start (5 minutes)

### 1. Clone and Setup
```bash
git clone https://github.com/your-org/ai-discovery-suite.git
cd ai-discovery-suite

# Copy environment configuration
cp .env.example .env

# Start everything with one command
make setup
```

### 2. Verify Installation
```bash
# Test all services
make test

# Or test manually
python test_system.py
```

### 3. Access Services
- **Search Service**: http://localhost:8001/docs
- **Recommendation Service**: http://localhost:8002/docs
- **Analytics Service**: http://localhost:8004/docs
- **Database Admin**: http://localhost:8090 (adminer)
- **Redis Commander**: http://localhost:8091
- **RabbitMQ Management**: http://localhost:15672

## 🔧 Manual Setup (Step by Step)

### 1. Environment Configuration
```bash
# Copy and edit environment file
cp .env.example .env
nano .env  # Adjust settings as needed
```

### 2. Build and Start Services
```bash
# Build all Docker images
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 3. Initialize Data
```bash
# The database will auto-initialize on first run
# Wait for services to be ready (about 30 seconds)

# Test search service
curl "http://localhost:8001/health"

# Test with sample data
curl "http://localhost:8001/search?q=laptop&store_id=1"
```

## 📦 Magento 2 Integration

### 1. Install the Module
```bash
# Option A: Copy module files manually
cp -r magento2-module/Vendor /path/to/your/magento/app/code/

# Option B: Use Composer (if packaged)
cd /path/to/your/magento
composer require vendor/discoverysuite
```

### 2. Enable and Configure
```bash
cd /path/to/your/magento

# Enable the module
php bin/magento module:enable Vendor_DiscoverySuite
php bin/magento setup:upgrade
php bin/magento cache:flush

# Configure in Admin
# Go to: Stores > Configuration > AI Discovery Suite
# Set API Base URL: http://localhost (or your server IP)
# Add API Key if required
```

### 3. Sync Product Catalog
```bash
# From Magento
php bin/magento discovery:catalog:sync

# Or directly via API
curl -X POST "http://localhost:8001/index/rebuild" \
  -H "Content-Type: application/json" \
  -d '{"store_id": 1}'
```

## 🧪 Testing the System

### Automated Testing
```bash
# Run all tests
make test

# Test specific services
make test-search
make test-api

# Comprehensive system test
python test_system.py
```

### Manual Testing

#### 1. Search Functionality
```bash
# Basic search
curl "http://localhost:8001/search?q=laptop&store_id=1&limit=5"

# Autocomplete
curl "http://localhost:8001/autocomplete?q=lap&store_id=1"

# Suggestions
curl "http://localhost:8001/suggestions?q=laptp&store_id=1"
```

#### 2. Recommendations
```bash
# Homepage recommendations
curl "http://localhost:8002/recommendations?context=homepage&store_id=1"

# Product page recommendations
curl "http://localhost:8002/recommendations?context=product&product_id=1&store_id=1"
```

#### 3. Analytics
```bash
# Track an event
curl -X POST "http://localhost:8004/track" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "search",
    "event_data": {"query": "laptop", "results": 10},
    "store_id": 1,
    "session_id": "test123"
  }'

# Get analytics
curl "http://localhost:8004/dashboard?store_id=1&period=week"
```

## 🔍 Monitoring and Debugging

### Service Logs
```bash
# All services
make logs

# Specific service
make logs-search
make logs-db

# Or with Docker Compose
docker-compose logs -f search-service
```

### Health Checks
```bash
# Check all service health
make status

# Individual health checks
curl http://localhost:8001/health  # Search
curl http://localhost:8002/health  # Recommendations
curl http://localhost:8004/health  # Analytics
```

### Database Access
```bash
# Via Adminer web interface
open http://localhost:8090

# Via command line
make shell-db
# Or: docker-compose exec postgres psql -U discovery -d discovery_suite
```

### Redis Access
```bash
# Via Redis Commander web interface
open http://localhost:8091

# Via command line
make shell-redis
# Or: docker-compose exec redis redis-cli
```

## ⚡ Performance Optimization

### 1. Resource Allocation
```yaml
# In docker-compose.yml, add resource limits:
services:
  search-service:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### 2. Elasticsearch Tuning
```bash
# Increase heap size for Elasticsearch
echo "ES_JAVA_OPTS=-Xms2g -Xmx2g" >> .env
```

### 3. Database Optimization
```sql
-- Connect to database and run optimizations
-- make shell-db

-- Create additional indexes for better performance
CREATE INDEX CONCURRENTLY idx_products_search_vector ON products USING GIN (searchable_text);
CREATE INDEX CONCURRENTLY idx_search_queries_performance ON search_queries (created_at, store_id, total_results);
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Services Won't Start
```bash
# Check Docker resources
docker system df
docker system prune  # Clean up if needed

# Check port conflicts
netstat -tulpn | grep :8001  # Or ss -tulpn

# Restart with fresh volumes
make clean
make up
```

#### 2. Out of Memory
```bash
# Reduce resource usage
export ELASTICSEARCH_HEAP_SIZE=512m
export POSTGRES_SHARED_BUFFERS=256MB

# Or scale down services
docker-compose up search-service postgres redis  # Start only essential services
```

#### 3. Database Connection Issues
```bash
# Check database logs
make logs-db

# Reset database
docker-compose down postgres
docker volume rm ai-product-discovery_postgres_data
docker-compose up postgres
```

#### 4. Search Not Working
```bash
# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Rebuild search index
curl -X POST "http://localhost:8001/index/rebuild" -d '{"store_id": 1}'

# Check search service logs
make logs-search
```

### Getting Help

1. **Check service logs** with `make logs`
2. **Run system tests** with `python test_system.py`
3. **Verify configuration** in `.env` file
4. **Check resource usage** with `docker stats`
5. **Review documentation** in `/docs` folder

## 🔒 Security Considerations

### Production Deployment

1. **Change default passwords**:
   ```bash
   # Update .env file
   POSTGRES_PASSWORD=your-secure-password
   RABBITMQ_DEFAULT_PASS=your-secure-password
   SECRET_KEY=your-very-long-random-secret-key
   ```

2. **Enable authentication**:
   ```bash
   # For Elasticsearch
   ELASTICSEARCH_USERNAME=discovery
   ELASTICSEARCH_PASSWORD=your-secure-password
   
   # For Redis
   REDIS_PASSWORD=your-secure-password
   ```

3. **Use HTTPS**:
   - Set up reverse proxy (nginx/traefik)
   - Configure SSL certificates
   - Update CORS origins

4. **Restrict network access**:
   - Use Docker networks
   - Configure firewall rules
   - Limit exposed ports

## 🎯 Next Steps

1. **Customize AI models** in `backend/shared/config/settings.py`
2. **Add custom product attributes** in product indexing
3. **Configure A/B testing** for optimization
4. **Set up monitoring** with Prometheus/Grafana
5. **Scale services** with Docker Swarm or Kubernetes

## 📞 Support

- **Documentation**: Check the `/docs` folder
- **Issues**: Create GitHub issues for bugs
- **Community**: Join our Discord server
- **Enterprise**: Contact sales@discoverysuite.ai

---

🎉 **Congratulations!** Your AI Product Discovery Suite is now running. Happy discovering! 🚀