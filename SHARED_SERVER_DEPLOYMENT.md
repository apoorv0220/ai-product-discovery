# 🚀 AI Product Discovery Suite - Shared Server Deployment Guide
*Complete step-by-step guide for beginners*

## 📋 Table of Contents
1. [Pre-requisites Check](#pre-requisites-check)
2. [Server Preparation](#server-preparation)
3. [Download & Setup Project](#download--setup-project)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Python Services Deployment](#python-services-deployment)
7. [Web Server Configuration](#web-server-configuration)
8. [Magento 2 Integration](#magento-2-integration)
9. [Testing & Verification](#testing--verification)
10. [Monitoring & Maintenance](#monitoring--maintenance)
11. [Troubleshooting](#troubleshooting)

---

## 🔍 Pre-requisites Check

### ✅ **What You Need on Your Server:**
- **PostgreSQL** running on port 5432 ✅ (You have this)
- **Redis** running on port 6379 ✅ (You have this)
- **Python 3.8+** (We'll install if needed)
- **Node.js 16+** (For some utilities)
- **Web Server** (Apache/Nginx)
- **SSH Access** to your server
- **Domain/Subdomain** for your APIs

### 🔍 **Check What's Available:**
```bash
# SSH into your server first
ssh your-username@your-server.com

# Check PostgreSQL
psql --version
sudo systemctl status postgresql

# Check Redis
redis-cli ping
sudo systemctl status redis

# Check Python
python3 --version
pip3 --version

# Check available ports
sudo netstat -tulpn | grep -E ':(5432|6379|80|443|8001|8002|8004|8005)'
```

---

## 🛠️ Server Preparation

### **Step 1: Update System**
```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git unzip vim htop
```

### **Step 2: Install Python & Dependencies**
```bash
# Install Python 3.8+ and pip
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install PostgreSQL client tools
sudo apt install -y postgresql-client libpq-dev

# Install Redis tools (if not available)
sudo apt install -y redis-tools

# Install build tools for Python packages
sudo apt install -y build-essential gcc
```

### **Step 3: Install Node.js (Optional but recommended)**
```bash
# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### **Step 4: Create Application User (Security Best Practice)**
```bash
# Create dedicated user for the application
sudo useradd -m -s /bin/bash aiproduct
sudo usermod -aG www-data aiproduct

# Set up sudo access (if needed)
sudo usermod -aG sudo aiproduct

# Switch to application user
sudo su - aiproduct
```

---

## 📥 Download & Setup Project

### **Step 1: Clone Repository**
```bash
# Navigate to user home directory
cd /home/aiproduct

# Clone your project (replace with your repository URL)
git clone https://github.com/your-username/ai-product-discovery.git
cd ai-product-discovery

# Or download if no git repository
# wget https://github.com/your-repo/archive/main.zip
# unzip main.zip && mv ai-product-discovery-main ai-product-discovery
```

### **Step 2: Create Directory Structure**
```bash
# Create application directories
mkdir -p /home/aiproduct/apps
mkdir -p /home/aiproduct/logs
mkdir -p /home/aiproduct/data
mkdir -p /home/aiproduct/backups

# Move project to apps directory
mv ai-product-discovery /home/aiproduct/apps/
cd /home/aiproduct/apps/ai-product-discovery
```

### **Step 3: Set Permissions**
```bash
# Set proper ownership
sudo chown -R aiproduct:www-data /home/aiproduct/apps/
sudo chmod -R 755 /home/aiproduct/apps/

# Make scripts executable
chmod +x scripts/*.sh
chmod +x *.sh
```

---

## ⚙️ Environment Configuration

### **Step 1: Create Production Environment File**
```bash
cd /home/aiproduct/apps/ai-product-discovery

# Create production environment file
cp .env.example .env.production

# Edit the environment file
nano .env.production
```

### **Step 2: Configure Environment Variables**
```bash
# .env.production content:

# ===============================
# SHARED SERVER CONFIGURATION
# ===============================

# Database Configuration (Use your existing PostgreSQL)
DATABASE_URL=postgresql://your_db_user:your_db_password@localhost:5432/ai_discovery
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_discovery
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password

# Redis Configuration (Use your existing Redis)
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Service Configuration (Use different ports for shared server)
SEARCH_SERVICE_HOST=0.0.0.0
SEARCH_SERVICE_PORT=8001

RECOMMENDATION_SERVICE_HOST=0.0.0.0
RECOMMENDATION_SERVICE_PORT=8002

ANALYTICS_SERVICE_HOST=0.0.0.0
ANALYTICS_SERVICE_PORT=8004

SHOPPING_ASSISTANT_HOST=0.0.0.0
SHOPPING_ASSISTANT_PORT=8005

# API Configuration
API_V1_PREFIX=/api/v1
API_TITLE=AI Product Discovery Suite
API_VERSION=1.0.0

# Security
SECRET_KEY=your-super-secret-key-here-change-this
JWT_SECRET_KEY=your-jwt-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External Services (Optional - set if you have them)
ELASTICSEARCH_URL=http://localhost:9200
WEAVIATE_URL=http://localhost:8080

# Celery Configuration (Optional - for background tasks)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Environment
ENVIRONMENT=production
DEBUG=false
```

### **Step 3: Secure Environment File**
```bash
# Set secure permissions for environment file
chmod 600 .env.production

# Create symlink for easy access
ln -sf .env.production .env
```

---

## 🗄️ Database Setup

### **Step 1: Create Database and User**
```bash
# Connect to PostgreSQL as admin user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE ai_discovery;
CREATE USER ai_user WITH ENCRYPTED PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE ai_discovery TO ai_user;

# Grant additional permissions
\c ai_discovery
GRANT ALL ON SCHEMA public TO ai_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_user;

# Exit PostgreSQL
\q
```

### **Step 2: Test Database Connection**
```bash
# Test connection with your new user
psql -h localhost -p 5432 -U ai_user -d ai_discovery

# If successful, you'll see:
# ai_discovery=>

# Exit
\q
```

### **Step 3: Update Environment with Database Credentials**
```bash
# Edit .env.production with your actual database credentials
nano .env.production

# Update these lines:
DATABASE_URL=postgresql://ai_user:secure_password_123@localhost:5432/ai_discovery
POSTGRES_USER=ai_user
POSTGRES_PASSWORD=secure_password_123
```

---

## 🐍 Python Services Deployment

### **Step 1: Create Virtual Environment**
```bash
cd /home/aiproduct/apps/ai-product-discovery

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### **Step 2: Install Python Dependencies**
```bash
# Install base requirements first
pip install -r backend/requirements-base.txt

# Install full requirements
pip install -r backend/requirements.txt

# Install additional production dependencies
pip install gunicorn supervisor
```

### **Step 3: Initialize Database Tables**
```bash
# Set environment
export $(cat .env.production | xargs)

# Initialize database tables
cd backend
python -c "
import asyncio
from shared.database.base import init_database

async def setup():
    await init_database()
    print('Database initialized successfully!')

asyncio.run(setup())
"
```

### **Step 4: Create Service Start Scripts**

#### **Search Service Startup Script:**
```bash
# Create search service script
cat > /home/aiproduct/apps/ai-product-discovery/start_search.sh << 'EOF'
#!/bin/bash
cd /home/aiproduct/apps/ai-product-discovery
source venv/bin/activate
export $(cat .env.production | xargs)

# Start Search Service
cd backend/search-service
gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001 --access-logfile /home/aiproduct/logs/search_access.log --error-logfile /home/aiproduct/logs/search_error.log --daemon
EOF

chmod +x start_search.sh
```

#### **Recommendation Service Startup Script:**
```bash
cat > start_recommendation.sh << 'EOF'
#!/bin/bash
cd /home/aiproduct/apps/ai-product-discovery
source venv/bin/activate
export $(cat .env.production | xargs)

cd backend/recommendation-service
gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8002 --access-logfile /home/aiproduct/logs/recommendation_access.log --error-logfile /home/aiproduct/logs/recommendation_error.log --daemon
EOF

chmod +x start_recommendation.sh
```

#### **Analytics Service Startup Script:**
```bash
cat > start_analytics.sh << 'EOF'
#!/bin/bash
cd /home/aiproduct/apps/ai-product-discovery
source venv/bin/activate
export $(cat .env.production | xargs)

cd backend/analytics-service
gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8004 --access-logfile /home/aiproduct/logs/analytics_access.log --error-logfile /home/aiproduct/logs/analytics_error.log --daemon
EOF

chmod +x start_analytics.sh
```

#### **Shopping Assistant Startup Script:**
```bash
cat > start_shopping_assistant.sh << 'EOF'
#!/bin/bash
cd /home/aiproduct/apps/ai-product-discovery
source venv/bin/activate
export $(cat .env.production | xargs)

cd backend/shopping-assistant
gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8005 --access-logfile /home/aiproduct/logs/shopping_assistant_access.log --error-logfile /home/aiproduct/logs/shopping_assistant_error.log --daemon
EOF

chmod +x start_shopping_assistant.sh
```

#### **Master Startup Script:**
```bash
cat > start_all_services.sh << 'EOF'
#!/bin/bash
echo "Starting AI Product Discovery Suite..."

# Start all services
./start_search.sh
sleep 2
./start_recommendation.sh
sleep 2
./start_analytics.sh
sleep 2
./start_shopping_assistant.sh

echo "All services started!"
echo "Check logs in /home/aiproduct/logs/"
EOF

chmod +x start_all_services.sh
```

### **Step 5: Start Services**
```bash
# Start all services
./start_all_services.sh

# Check if services are running
ps aux | grep gunicorn

# Check logs
tail -f /home/aiproduct/logs/*.log
```

---

## 🌐 Web Server Configuration

### **Option A: Using Nginx (Recommended)**

#### **Step 1: Install Nginx**
```bash
sudo apt install -y nginx
```

#### **Step 2: Create API Configuration**
```bash
sudo nano /etc/nginx/sites-available/ai-discovery-api
```

#### **Step 3: Nginx Configuration Content:**
```nginx
server {
    listen 80;
    server_name your-api-domain.com;  # Replace with your domain

    # API Routes
    location /api/v1/search/ {
        proxy_pass http://localhost:8001/api/v1/search/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/recommendations/ {
        proxy_pass http://localhost:8002/api/v1/recommendations/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/analytics/ {
        proxy_pass http://localhost:8004/api/v1/analytics/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/chat/ {
        proxy_pass http://localhost:8005/api/v1/chat/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health checks
    location /health {
        proxy_pass http://localhost:8001/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Static files (if any)
    location /static/ {
        alias /home/aiproduct/apps/ai-product-discovery/static/;
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
```

#### **Step 4: Enable Site**
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/ai-discovery-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### **Option B: Using Apache**

#### **Step 1: Install Apache**
```bash
sudo apt install -y apache2
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod headers
```

#### **Step 2: Create Virtual Host**
```bash
sudo nano /etc/apache2/sites-available/ai-discovery-api.conf
```

#### **Step 3: Apache Configuration:**
```apache
<VirtualHost *:80>
    ServerName your-api-domain.com
    DocumentRoot /home/aiproduct/apps/ai-product-discovery

    # API Proxies
    ProxyPreserveHost On
    
    ProxyPass /api/v1/search/ http://localhost:8001/api/v1/search/
    ProxyPassReverse /api/v1/search/ http://localhost:8001/api/v1/search/
    
    ProxyPass /api/v1/recommendations/ http://localhost:8002/api/v1/recommendations/
    ProxyPassReverse /api/v1/recommendations/ http://localhost:8002/api/v1/recommendations/
    
    ProxyPass /api/v1/analytics/ http://localhost:8004/api/v1/analytics/
    ProxyPassReverse /api/v1/analytics/ http://localhost:8004/api/v1/analytics/
    
    ProxyPass /api/v1/chat/ http://localhost:8005/api/v1/chat/
    ProxyPassReverse /api/v1/chat/ http://localhost:8005/api/v1/chat/
    
    ProxyPass /health http://localhost:8001/health
    ProxyPassReverse /health http://localhost:8001/health

    # Security Headers
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
    
    ErrorLog ${APACHE_LOG_DIR}/ai-discovery-error.log
    CustomLog ${APACHE_LOG_DIR}/ai-discovery-access.log combined
</VirtualHost>
```

#### **Step 4: Enable Site**
```bash
sudo a2ensite ai-discovery-api.conf
sudo systemctl restart apache2
sudo systemctl enable apache2
```

---

## 🛒 Magento 2 Integration

### **Step 1: Copy Magento Module**
```bash
# If Magento is on the same server
sudo cp -r /home/aiproduct/apps/ai-product-discovery/magento2-module/Vendor /path/to/your/magento/app/code/

# If Magento is on different server, create a zip
cd /home/aiproduct/apps/ai-product-discovery/magento2-module
zip -r DiscoverySuite.zip Vendor/
# Transfer this to your Magento server
```

### **Step 2: Install Module in Magento**
```bash
# On your Magento server
cd /path/to/your/magento

# Enable module
php bin/magento module:enable Vendor_DiscoverySuite

# Run setup
php bin/magento setup:upgrade
php bin/magento setup:di:compile
php bin/magento setup:static-content:deploy

# Clear cache
php bin/magento cache:clean
php bin/magento cache:flush
```

### **Step 3: Configure Magento Module**
```bash
# Edit Magento configuration
# Admin Panel > Stores > Configuration > Vendor > Discovery Suite

# Or via CLI:
php bin/magento config:set discovery_suite/api/search_endpoint "http://your-api-domain.com/api/v1/search/"
php bin/magento config:set discovery_suite/api/recommendation_endpoint "http://your-api-domain.com/api/v1/recommendations/"
php bin/magento config:set discovery_suite/api/analytics_endpoint "http://your-api-domain.com/api/v1/analytics/"
php bin/magento config:set discovery_suite/api/assistant_endpoint "http://your-api-domain.com/api/v1/chat/"
```

---

## 🧪 Testing & Verification

### **Step 1: Test Individual Services**
```bash
# Test Search Service
curl -X GET "http://your-domain.com/api/v1/search/health"

# Test with actual search
curl -X POST "http://your-domain.com/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "laptop", "limit": 5}'

# Test Recommendations
curl -X POST "http://your-domain.com/api/v1/recommendations/" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "context": "home", "limit": 8}'
```

### **Step 2: Run Verification Script**
```bash
cd /home/aiproduct/apps/ai-product-discovery

# Update verification script for your domain
sed -i 's/localhost/your-domain.com/g' scripts/verify_localhost.py

# Run verification
python3 scripts/verify_localhost.py
```

### **Step 3: Load Dummy Data (Optional)**
```bash
# Load test data for demonstration
python3 scripts/init_dummy_data.py
```

---

## 📊 Monitoring & Maintenance

### **Step 1: Create System Service Files**

#### **Search Service:**
```bash
sudo nano /etc/systemd/system/ai-search.service
```

```ini
[Unit]
Description=AI Discovery Search Service
After=network.target postgresql.service redis.service

[Service]
Type=forking
User=aiproduct
WorkingDirectory=/home/aiproduct/apps/ai-product-discovery
ExecStart=/home/aiproduct/apps/ai-product-discovery/start_search.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### **Create Services for All Components:**
```bash
# Create similar service files for other services
sudo cp /etc/systemd/system/ai-search.service /etc/systemd/system/ai-recommendation.service
sudo cp /etc/systemd/system/ai-search.service /etc/systemd/system/ai-analytics.service
sudo cp /etc/systemd/system/ai-search.service /etc/systemd/system/ai-shopping-assistant.service

# Update ExecStart paths in each file
sudo nano /etc/systemd/system/ai-recommendation.service
# Change: ExecStart=/home/aiproduct/apps/ai-product-discovery/start_recommendation.sh

# Repeat for other services...
```

#### **Enable Services:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-search ai-recommendation ai-analytics ai-shopping-assistant
sudo systemctl start ai-search ai-recommendation ai-analytics ai-shopping-assistant
```

### **Step 2: Setup Log Rotation**
```bash
sudo nano /etc/logrotate.d/ai-discovery
```

```bash
/home/aiproduct/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 aiproduct aiproduct
}
```

### **Step 3: Setup Monitoring Script**
```bash
cat > /home/aiproduct/monitor_services.sh << 'EOF'
#!/bin/bash

SERVICES=("ai-search" "ai-recommendation" "ai-analytics" "ai-shopping-assistant")
ENDPOINTS=("8001" "8002" "8004" "8005")

echo "$(date): Checking AI Discovery Services..." >> /home/aiproduct/logs/monitor.log

for i in "${!SERVICES[@]}"; do
    SERVICE="${SERVICES[$i]}"
    PORT="${ENDPOINTS[$i]}"
    
    # Check if service is running
    if systemctl is-active --quiet $SERVICE; then
        echo "✅ $SERVICE is running"
    else
        echo "❌ $SERVICE is not running - attempting restart"
        sudo systemctl restart $SERVICE
        echo "$(date): Restarted $SERVICE" >> /home/aiproduct/logs/monitor.log
    fi
    
    # Check if port is responding
    if curl -s http://localhost:$PORT/health > /dev/null; then
        echo "✅ $SERVICE responding on port $PORT"
    else
        echo "❌ $SERVICE not responding on port $PORT"
        echo "$(date): $SERVICE not responding on port $PORT" >> /home/aiproduct/logs/monitor.log
    fi
done
EOF

chmod +x /home/aiproduct/monitor_services.sh

# Add to crontab for automatic monitoring
crontab -e
# Add this line:
# */5 * * * * /home/aiproduct/monitor_services.sh
```

---

## 🔧 Troubleshooting

### **Common Issues and Solutions:**

#### **1. Services Not Starting**
```bash
# Check logs
tail -f /home/aiproduct/logs/*_error.log

# Check if ports are available
sudo netstat -tulpn | grep -E ':(8001|8002|8004|8005)'

# Check virtual environment
source /home/aiproduct/apps/ai-product-discovery/venv/bin/activate
python -c "import fastapi; print('FastAPI OK')"
```

#### **2. Database Connection Issues**
```bash
# Test database connection
psql -h localhost -p 5432 -U ai_user -d ai_discovery -c "SELECT version();"

# Check if database exists
sudo -u postgres psql -c "\l" | grep ai_discovery
```

#### **3. Permission Issues**
```bash
# Fix ownership
sudo chown -R aiproduct:www-data /home/aiproduct/apps/
sudo chmod -R 755 /home/aiproduct/apps/

# Fix log permissions
sudo chown -R aiproduct:www-data /home/aiproduct/logs/
sudo chmod -R 644 /home/aiproduct/logs/
```

#### **4. Memory Issues**
```bash
# Check memory usage
free -h

# Check processes
top -u aiproduct

# Reduce workers if needed (edit start scripts)
# Change: -w 2 to -w 1
```

#### **5. Network Issues**
```bash
# Check if services are listening
sudo ss -tulpn | grep -E ':(8001|8002|8004|8005)'

# Test internal connectivity
curl http://localhost:8001/health
curl http://localhost:8002/health
```

---

## 🎯 Final Checklist

### ✅ **Deployment Checklist:**
- [ ] PostgreSQL and Redis accessible
- [ ] Python environment setup
- [ ] All dependencies installed
- [ ] Database created and initialized
- [ ] Environment variables configured
- [ ] All services starting successfully
- [ ] Web server (Nginx/Apache) configured
- [ ] API endpoints accessible
- [ ] Magento module installed
- [ ] Monitoring setup
- [ ] SSL certificate (optional but recommended)

### 🚀 **Your APIs are now available at:**
- **Search**: `http://your-domain.com/api/v1/search/`
- **Recommendations**: `http://your-domain.com/api/v1/recommendations/`
- **Analytics**: `http://your-domain.com/api/v1/analytics/`
- **Shopping Assistant**: `http://your-domain.com/api/v1/chat/`

### 📞 **Need Help?**
If you encounter any issues:

1. **Check logs**: `/home/aiproduct/logs/`
2. **Verify services**: `sudo systemctl status ai-search`
3. **Test connectivity**: `curl http://localhost:8001/health`
4. **Check resources**: `htop` or `free -h`

Your AI Product Discovery Suite is now deployed on your shared server! 🎉