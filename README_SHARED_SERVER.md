# 🚀 AI Product Discovery Suite - Shared Server Deployment

*Perfect for beginners new to server deployment!*

## 🎯 **What This Gives You**

Your AI Product Discovery Suite will run on your shared server using your existing PostgreSQL and Redis services, providing:

- **🔍 Intelligent Search API** - Advanced product search with AI
- **🤖 Recommendation Engine** - Personalized product suggestions  
- **📊 Analytics Platform** - User behavior tracking and insights
- **🛍️ Shopping Assistant** - AI-powered customer support
- **🔗 Magento 2 Integration** - Seamless e-commerce integration

---

## 📚 **Documentation Guide**

### **🚀 Quick Start (30 minutes)**
1. **[QUICK_DEPLOYMENT_CHECKLIST.md](QUICK_DEPLOYMENT_CHECKLIST.md)** - Step-by-step checklist
2. **Run:** `./deploy_shared_server.sh` - Automated deployment script

### **📖 Detailed Guides**
1. **[SHARED_SERVER_DEPLOYMENT.md](SHARED_SERVER_DEPLOYMENT.md)** - Complete deployment guide
2. **[.env.shared-server](.env.shared-server)** - Environment configuration template

### **🔧 Management**
- **Start Services:** `./control_services.sh start`
- **Check Status:** `./control_services.sh status` 
- **Test APIs:** `./test_deployment.sh`

---

## ⚡ **Super Quick Setup**

```bash
# 1. SSH into your server
ssh username@your-server.com

# 2. Upload project files
git clone https://github.com/your-repo/ai-product-discovery.git
cd ai-product-discovery

# 3. Run automated deployment
chmod +x deploy_shared_server.sh
./deploy_shared_server.sh

# 4. Setup web server (Nginx)
sudo cp nginx_ai_discovery.conf /etc/nginx/sites-available/ai-discovery
sudo ln -s /etc/nginx/sites-available/ai-discovery /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# 5. Test deployment
./test_deployment.sh
```

**That's it!** Your APIs will be live at `http://your-domain.com/api/v1/`

---

## 🛠️ **What You Need**

### **✅ Server Requirements**
- PostgreSQL running on port 5432 *(You have this)*
- Redis running on port 6379 *(You have this)*
- Python 3.8+ *(Script will install)*
- SSH access *(You have this)*
- Domain/subdomain for APIs

### **🔧 Ports Used**
- **8001** - Search Service
- **8002** - Recommendation Service  
- **8004** - Analytics Service
- **8005** - Shopping Assistant Service

*These can be changed in the environment configuration*

---

## 📊 **Your API Endpoints**

Once deployed, your APIs will be available at:

| Service | Endpoint | Example |
|---------|----------|---------|
| **Search** | `/api/v1/search/` | Product search & autocomplete |
| **Recommendations** | `/api/v1/recommendations/` | Personalized suggestions |
| **Analytics** | `/api/v1/analytics/` | Event tracking |
| **Assistant** | `/api/v1/chat/` | AI shopping help |
| **Health** | `/health` | Service status |

### **Example API Calls:**
```bash
# Search products
curl -X POST "http://your-domain.com/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "laptop", "limit": 5}'

# Get recommendations  
curl -X POST "http://your-domain.com/api/v1/recommendations/" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "123", "context": "home", "limit": 8}'
```

---

## 🎛️ **Management Commands**

```bash
# Service Control
./control_services.sh start     # Start all services
./control_services.sh stop      # Stop all services
./control_services.sh restart   # Restart all services
./control_services.sh status    # Check status

# Testing & Monitoring
./test_deployment.sh           # Test all APIs
tail -f ~/logs/*.log          # View logs
```

---

## 🔒 **Security & Production**

### **Environment Configuration**
```bash
# Your environment file (.env.production) will contain:
DATABASE_URL=postgresql://user:pass@localhost:5432/ai_discovery
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
API_DOMAIN=your-domain.com
```

### **SSL Certificate (Recommended)**
```bash
# Install SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 🚦 **Monitoring & Health**

### **Service Status**
```bash
# Quick status check
./control_services.sh status

# Expected output:
# ✅ search: Running (PID: 1234, Port: 8001) - Healthy
# ✅ recommendation: Running (PID: 1235, Port: 8002) - Healthy
# ✅ analytics: Running (PID: 1236, Port: 8004) - Healthy
# ✅ shopping_assistant: Running (PID: 1237, Port: 8005) - Healthy
```

### **Log Monitoring**
```bash
# All logs
tail -f ~/logs/*.log

# Specific service
tail -f ~/logs/search_error.log
tail -f ~/logs/recommendation_access.log
```

---

## 🛒 **Magento 2 Integration**

After your APIs are running:

```bash
# 1. Copy Magento module
cp -r magento2-module/Vendor /path/to/magento/app/code/

# 2. Install in Magento
php bin/magento module:enable Vendor_DiscoverySuite
php bin/magento setup:upgrade

# 3. Configure API endpoints in Magento Admin:
# Stores > Configuration > Vendor > Discovery Suite
# Set API Base URL: http://your-domain.com
```

---

## 🎯 **Success Checklist**

After deployment, verify these work:

- [ ] **Health Check:** `curl http://your-domain.com/health` returns OK
- [ ] **Search API:** Returns product results
- [ ] **Recommendations:** Returns product suggestions  
- [ ] **Analytics:** Accepts tracking events
- [ ] **Assistant:** Responds to chat messages
- [ ] **Logs:** No critical errors in log files
- [ ] **Nginx:** Web server proxying requests correctly

---

## ❓ **Troubleshooting**

### **Services Won't Start**
```bash
# Check logs
tail -f ~/logs/*_error.log

# Check if ports are available
sudo netstat -tulpn | grep -E ':(8001|8002|8004|8005)'

# Restart individual service
./start_search.sh
```

### **Database Issues**
```bash
# Test connection
psql -h localhost -U aiproduct -d ai_discovery

# Check PostgreSQL status
sudo systemctl status postgresql
```

### **Nginx 502/504 Errors**
```bash
# Check if services are responding
curl http://localhost:8001/health

# Check Nginx configuration
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

---

## 📞 **Support**

Need help? Check these in order:

1. **📋 [QUICK_DEPLOYMENT_CHECKLIST.md](QUICK_DEPLOYMENT_CHECKLIST.md)** - Step-by-step guide
2. **📚 [SHARED_SERVER_DEPLOYMENT.md](SHARED_SERVER_DEPLOYMENT.md)** - Detailed documentation
3. **🔍 Logs:** `tail -f ~/logs/*.log` - Check for errors
4. **⚡ Status:** `./control_services.sh status` - Verify services

---

## 🎉 **You're All Set!**

Once deployed, your AI Product Discovery Suite will provide enterprise-level e-commerce intelligence using your existing server infrastructure. 

**Perfect for shared hosting environments!** 🚀

Your customers will get:
- ⚡ Lightning-fast search results
- 🎯 Personalized product recommendations  
- 🛍️ AI-powered shopping assistance
- 📊 Advanced analytics and insights

**Deploy once, scale everywhere!** 📈