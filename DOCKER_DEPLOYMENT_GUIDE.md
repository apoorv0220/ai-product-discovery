# 🐳 Docker Deployment Guide for Shared Server

This guide covers deploying the AI Product Discovery Suite using Docker containers while utilizing the host server's PostgreSQL and Redis.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Shared Server                             │
├─────────────────────────────────────────────────────────────┤
│  Host Services:                                             │
│  ├── PostgreSQL (localhost:5432)                           │
│  └── Redis (localhost:6379)                                │
├─────────────────────────────────────────────────────────────┤
│  Docker Containers:                                        │
│  ├── Search Service (port 7001)                            │
│  ├── Recommendation Service (port 7002)                    │
│  ├── Analytics Service (port 7004)                         │
│  ├── Shopping Assistant (port 7005)                        │
│  ├── Celery Worker                                         │
│  ├── Celery Flower (port 7006)                             │
│  └── Nginx Reverse Proxy (port 80/443)                     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
pip install docker-compose

# Or install via package manager
sudo apt-get install docker-compose
```

### 2. Deploy
```bash
# Option A: Quick deployment
./deploy_docker_shared_server.sh

# Option B: Step-by-step deployment
./fix_docker_host_networking.sh
./deploy_docker_shared_server.sh
```

### 3. Manage Services
```bash
# Control services
./docker_control.sh start|stop|restart|status|logs|build

# Test APIs
./test_docker_apis.sh

# Check connectivity
./test_container_connectivity.sh
```

## 📋 Detailed Deployment Steps

### Step 1: Network Configuration
```bash
# Fix Docker networking for Linux servers
./fix_docker_host_networking.sh
```

This script:
- ✅ Detects the correct host IP for Docker containers
- ✅ Tests PostgreSQL and Redis connectivity
- ✅ Updates Docker Compose and environment files
- ✅ Creates connectivity test scripts

### Step 2: Environment Setup
```bash
# The deployment script will prompt for:
# - PostgreSQL credentials
# - Redis connection details  
# - API domain/IP
# - Security keys (auto-generated)
```

### Step 3: Database Initialization
The script automatically:
- ✅ Creates required database tables
- ✅ Sets up proper indexes
- ✅ Configures connection pooling

### Step 4: Docker Services
Starts these containers:
- ✅ **Search Service**: Handles search queries and autocomplete
- ✅ **Recommendation Service**: Provides AI-powered recommendations
- ✅ **Analytics Service**: Tracks events and generates insights
- ✅ **Shopping Assistant**: AI chat interface
- ✅ **Celery Worker**: Background task processing
- ✅ **Celery Flower**: Task monitoring interface
- ✅ **Nginx**: Reverse proxy and load balancer

## 🔧 Configuration Files

### `docker-compose.shared-server.yml`
- Defines all Docker services
- Configures networking between containers
- Sets up port mappings and health checks

### `.env.docker-shared-server`
- Environment variables for all services
- Database and Redis connection strings
- Security keys and API configuration

### `nginx/shared-server.conf`
- Reverse proxy configuration
- API routing and load balancing
- Security headers and rate limiting

## 🌐 API Endpoints

Once deployed, your APIs will be available at:

| Service | Local Port | Nginx Route | Description |
|---------|------------|-------------|-------------|
| Search | 7001 | `/api/v1/search/` | Product search and autocomplete |
| Recommendations | 7002 | `/api/v1/recommendations/` | AI-powered product recommendations |
| Analytics | 7004 | `/api/v1/analytics/` | Event tracking and analytics |
| Shopping Assistant | 7005 | `/api/v1/chat/` | AI shopping assistant |
| Flower | 7006 | `/flower/` | Celery task monitoring |

### Example API Calls

```bash
# Search products
curl -X POST "http://localhost:7001/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "iPhone", "limit": 10}'

# Get recommendations
curl -X POST "http://localhost:7002/api/v1/recommendations/" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "123", "context": "home", "limit": 8}'

# Track events
curl -X POST "http://localhost:7004/api/v1/events/track" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "product_view", "user_id": "123", "product_id": "456"}'

# Chat with assistant
curl -X POST "http://localhost:7005/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "message": "Show me gaming laptops under $1000"}'
```

## 🛠️ Management Commands

### Service Control
```bash
# Start all services
./docker_control.sh start

# Stop all services
./docker_control.sh stop

# Restart services
./docker_control.sh restart

# Check service status
./docker_control.sh status

# View logs
./docker_control.sh logs

# Rebuild images
./docker_control.sh build
```

### Monitoring
```bash
# View real-time logs
docker-compose -f docker-compose.shared-server.yml logs -f

# Check container health
docker ps

# Monitor resource usage
docker stats

# Access Flower interface
open http://localhost:7006
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Container Can't Connect to Host Services
```bash
# Test connectivity
./test_container_connectivity.sh

# Check host IP detection
./fix_docker_host_networking.sh

# Manual connectivity test
docker run --rm alpine nc -zv 172.17.0.1 5432
docker run --rm alpine nc -zv 172.17.0.1 6379
```

#### 2. PostgreSQL Connection Failed
```bash
# Check PostgreSQL configuration
sudo nano /etc/postgresql/*/main/postgresql.conf
# Ensure: listen_addresses = '*'

sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add: host all all 172.17.0.0/16 md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 3. Redis Connection Failed
```bash
# Check Redis configuration
sudo nano /etc/redis/redis.conf
# Ensure: bind 127.0.0.1 172.17.0.1
# Comment out: # bind 127.0.0.1

# Restart Redis
sudo systemctl restart redis
```

#### 4. Docker Build Failures
```bash
# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker-compose -f docker-compose.shared-server.yml build --no-cache

# Check disk space
df -h
```

#### 5. Service Health Check Failures
```bash
# Check service logs
docker-compose -f docker-compose.shared-server.yml logs [service-name]

# Restart specific service
docker-compose -f docker-compose.shared-server.yml restart [service-name]

# Test service directly
curl -f http://localhost:7001/health
```

### Performance Optimization

#### 1. Resource Limits
Add to `docker-compose.shared-server.yml`:
```yaml
services:
  search-service:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

#### 2. Connection Pooling
Update `.env.docker-shared-server`:
```bash
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
REDIS_MAX_CONNECTIONS=50
```

#### 3. Caching
Enable Redis caching in services:
```bash
REDIS_CACHE_TTL=3600
ENABLE_QUERY_CACHE=true
```

## 🔒 Security Considerations

### 1. Environment Variables
```bash
# Secure environment file
chmod 600 .env.docker-shared-server

# Generate strong keys
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)
```

### 2. Database Security
```bash
# Create dedicated database user
sudo -u postgres createuser --interactive ai_discovery
sudo -u postgres createdb -O ai_discovery ai_discovery

# Set strong password
sudo -u postgres psql -c "ALTER USER ai_discovery PASSWORD 'strong_password_here';"
```

### 3. Network Security
```bash
# Limit Docker network access
sudo ufw allow from 172.17.0.0/16 to any port 5432
sudo ufw allow from 172.17.0.0/16 to any port 6379
```

### 4. SSL/TLS Setup
```bash
# Generate SSL certificate
sudo certbot --nginx -d your-domain.com

# Update nginx configuration
# Uncomment HTTPS block in nginx/shared-server.conf
```

## 📊 Monitoring and Logging

### 1. Centralized Logging
```bash
# Install logging driver
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions

# Update docker-compose.yml
logging:
  driver: loki
  options:
    loki-url: "http://localhost:3100/loki/api/v1/push"
```

### 2. Metrics Collection
```bash
# Add Prometheus monitoring
docker run -d --name prometheus \
  -p 9090:9090 \
  -v ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

### 3. Health Monitoring
```bash
# Set up health check alerts
curl -X POST http://localhost:7001/health || \
  echo "Search service down!" | mail -s "Alert" admin@yourdomain.com
```

## 🔄 Backup and Recovery

### 1. Database Backup
```bash
# Automated backup script
cat > backup_database.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U ai_discovery ai_discovery > "$BACKUP_DIR/ai_discovery_$DATE.sql"
EOF
```

### 2. Configuration Backup
```bash
# Backup configurations
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  docker-compose.shared-server.yml \
  .env.docker-shared-server \
  nginx/
```

### 3. Container Images Backup
```bash
# Save Docker images
docker save ai-discovery_search-service > search-service.tar
docker save ai-discovery_recommendation-service > recommendation-service.tar
```

## 🚀 Production Deployment Checklist

- [ ] ✅ PostgreSQL and Redis running on host
- [ ] ✅ Docker and Docker Compose installed
- [ ] ✅ Network connectivity between containers and host services
- [ ] ✅ Environment variables configured
- [ ] ✅ Database schema initialized
- [ ] ✅ Docker images built successfully
- [ ] ✅ All services healthy and responding
- [ ] ✅ API endpoints accessible
- [ ] ✅ SSL/TLS certificates configured (for production)
- [ ] ✅ Monitoring and logging set up
- [ ] ✅ Backup procedures in place
- [ ] ✅ Security measures implemented

## 🎯 Next Steps

1. **Integrate with Magento**: Update Magento configuration to use your Docker APIs
2. **Set up monitoring**: Add Prometheus + Grafana for comprehensive monitoring
3. **Configure alerts**: Set up email/Slack notifications for service issues
4. **Performance tuning**: Optimize based on your traffic patterns
5. **Scaling**: Add more replicas for high-traffic services

## 📞 Support

If you encounter issues:

1. **Check logs**: `./docker_control.sh logs`
2. **Test connectivity**: `./test_container_connectivity.sh`
3. **Verify configuration**: `docker-compose config`
4. **Check resources**: `docker stats`
5. **Restart services**: `./docker_control.sh restart`

For persistent issues, collect:
- Service logs
- Docker compose configuration
- Environment variables (sanitized)
- Host system information