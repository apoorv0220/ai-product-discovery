# ✅ Quick Deployment Checklist for Shared Server

## 🚀 **Before You Start**
- [ ] SSH access to your server
- [ ] PostgreSQL running on port 5432
- [ ] Redis running on port 6379  
- [ ] Domain/subdomain for your APIs
- [ ] Basic server admin knowledge

---

## 📋 **Step-by-Step Deployment** *(30-45 minutes)*

### **1. Server Preparation** *(5 mins)*
```bash
# SSH into your server
ssh username@your-server.com

# Update system
sudo apt update && sudo apt upgrade -y

# Install requirements
sudo apt install -y python3 python3-pip python3-venv postgresql-client redis-tools nginx
```

### **2. Create Application User** *(3 mins)*
```bash
# Create dedicated user
sudo useradd -m -s /bin/bash aiproduct
sudo usermod -aG www-data aiproduct

# Switch to user
sudo su - aiproduct
```

### **3. Deploy Application** *(10 mins)*
```bash
# Upload your project files or clone
git clone https://github.com/your-repo/ai-product-discovery.git
cd ai-product-discovery

# Run automated deployment script
chmod +x deploy_shared_server.sh
./deploy_shared_server.sh
```

**The script will ask you for:**
- PostgreSQL username/password
- Database name (default: ai_discovery)  
- Your domain/IP for APIs
- Whether to load demo data

### **4. Configure Database** *(5 mins)*
```bash
# Create database (if needed)
sudo -u postgres createdb ai_discovery
sudo -u postgres createuser aiproduct

# Set password
sudo -u postgres psql -c "ALTER USER aiproduct PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ai_discovery TO aiproduct;"
```

### **5. Setup Web Server** *(10 mins)*
```bash
# Copy Nginx config
sudo cp nginx_ai_discovery.conf /etc/nginx/sites-available/ai-discovery
sudo ln -s /etc/nginx/sites-available/ai-discovery /etc/nginx/sites-enabled/

# Update domain in config
sudo nano /etc/nginx/sites-available/ai-discovery
# Replace 'your-domain.com' with your actual domain

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
```

### **6. Start Services** *(2 mins)*
```bash
# Start all services
./control_services.sh start

# Check status
./control_services.sh status
```

### **7. Test Deployment** *(5 mins)*
```bash
# Run automated tests
./test_deployment.sh

# Manual test
curl http://your-domain.com/api/v1/search/health
```

---

## 🛠️ **Management Commands**

```bash
# Service Control
./control_services.sh start     # Start all services
./control_services.sh stop      # Stop all services  
./control_services.sh restart   # Restart all services
./control_services.sh status    # Check service status

# Testing
./test_deployment.sh            # Test all APIs

# View Logs
tail -f ~/logs/*.log            # Watch all logs
tail -f ~/logs/search_error.log # Specific service
```

---

## 📊 **Your APIs Will Be Available At:**

| Service | URL | Purpose |
|---------|-----|---------|
| **Search** | `http://your-domain.com/api/v1/search/` | Product search & autocomplete |
| **Recommendations** | `http://your-domain.com/api/v1/recommendations/` | Personalized recommendations |
| **Analytics** | `http://your-domain.com/api/v1/analytics/` | Event tracking & insights |
| **Shopping Assistant** | `http://your-domain.com/api/v1/chat/` | AI shopping assistant |
| **Health Check** | `http://your-domain.com/health` | Service health status |

---

## 🔧 **Common Issues & Solutions**

### **Services Not Starting**
```bash
# Check logs
tail -f ~/logs/*_error.log

# Check ports
sudo netstat -tulpn | grep -E ':(8001|8002|8004|8005)'

# Restart specific service
./start_search.sh
```

### **Database Connection Failed**
```bash
# Test connection
psql -h localhost -U aiproduct -d ai_discovery

# Check permissions
sudo -u postgres psql -c "\du"
```

### **Nginx 502 Error**
```bash
# Check if services are running
./control_services.sh status

# Check Nginx config
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### **Permission Issues**
```bash
# Fix ownership
sudo chown -R aiproduct:www-data ~/apps/
sudo chmod -R 755 ~/apps/
```

---

## 🎯 **Production Optimization**

### **1. Enable SSL (Recommended)**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

### **2. Setup Monitoring**
```bash
# Add to crontab
crontab -e

# Add this line for service monitoring
*/5 * * * * /home/aiproduct/apps/ai-product-discovery/control_services.sh status > /dev/null || /home/aiproduct/apps/ai-product-discovery/control_services.sh restart
```

### **3. Backup Strategy**
```bash
# Database backup
pg_dump -h localhost -U aiproduct ai_discovery > backup_$(date +%Y%m%d).sql

# Application backup
tar -czf app_backup_$(date +%Y%m%d).tar.gz ~/apps/ai-product-discovery/
```

---

## 🎉 **Success Indicators**

✅ All services show "Running - Healthy" in status  
✅ API endpoints return valid JSON responses  
✅ Nginx serves requests without 502/504 errors  
✅ Database connections work  
✅ Logs show no critical errors  

---

## 📞 **Need Help?**

1. **Check logs first**: `tail -f ~/logs/*.log`
2. **Verify services**: `./control_services.sh status`  
3. **Test APIs**: `./test_deployment.sh`
4. **Check resources**: `htop` or `free -h`

Your AI Product Discovery Suite should now be running successfully! 🚀