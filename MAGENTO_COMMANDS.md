# Complete Server Deployment Guide

## 🚀 PART 1: AI BACKEND SERVICES DEPLOYMENT

### Prerequisites
```bash
# Install Docker (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Python dependencies
sudo apt update
sudo apt install python3-pip python3-venv redis-server -y
```

### AI Backend Deployment
```bash
# 1. Navigate to project directory
cd /path/to/ai-product-discovery

# 2. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Start Redis server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 5. Start AI services in background
nohup python -m uvicorn backend.search-service.main:app --host 0.0.0.0 --port 7001 > search-service.log 2>&1 &
nohup python -m uvicorn backend.recommendation-service.main:app --host 0.0.0.0 --port 7002 > recommendation-service.log 2>&1 &
nohup python -m uvicorn backend.analytics-service.main:app --host 0.0.0.0 --port 7003 > analytics-service.log 2>&1 &
nohup python -m uvicorn backend.shopping-assistant.main:app --host 0.0.0.0 --port 7004 > shopping-assistant.log 2>&1 &

# 6. Verify services are running
curl http://localhost:7001/health
curl http://localhost:7002/health
curl http://localhost:7003/health
curl http://localhost:7004/health
```

## 🎯 PART 2: MAGENTO MODULE DEPLOYMENT

### Module Installation & Compilation
```bash
# Navigate to Magento root
cd /home/magentotests/public_html

# Enable the module
php bin/magento module:enable Vendor_DiscoverySuite

# Compile dependency injection
php bin/magento setup:di:compile

# Deploy static content (if needed)
php bin/magento setup:static-content:deploy

# Clear all caches
php bin/magento cache:flush
```

### AI Features Configuration
```bash
# Enable core functionality
php bin/magento config:set discovery_suite_config/general/enabled 1
php bin/magento config:set discovery_suite_config/search/enabled 1
php bin/magento config:set discovery_suite_config/search/autocomplete_enabled 1
php bin/magento config:set discovery_suite_config/recommendations/enabled 1

# Enable Advanced AI Features
php bin/magento config:set discovery_suite_config/search/nlp_enabled 1
php bin/magento config:set discovery_suite_config/search/typo_tolerance 1
php bin/magento config:set discovery_suite_config/search/intent_recognition 1
php bin/magento config:set discovery_suite_config/search/semantic_search 1
php bin/magento config:set discovery_suite_config/recommendations/ml_powered 1
php bin/magento config:set discovery_suite_config/recommendations/real_time_learning 1
php bin/magento config:set discovery_suite_config/recommendations/collaborative_filtering 1
php bin/magento config:set discovery_suite_config/recommendations/content_based 1
php bin/magento config:set discovery_suite_config/shopping_assistant/conversational_ai 1
php bin/magento config:set discovery_suite_config/shopping_assistant/nlp_processing 1
php bin/magento config:set discovery_suite_config/shopping_assistant/multi_turn_conversations 1
php bin/magento config:set discovery_suite_config/analytics/real_time_tracking 1
php bin/magento config:set discovery_suite_config/analytics/behavioral_insights 1
php bin/magento config:set discovery_suite_config/analytics/ab_testing 1
php bin/magento config:set discovery_suite_config/analytics/predictive_analytics 1

# Configure API endpoints (CRITICAL - Update with your server details)
php bin/magento config:set discovery_suite_config/api/search_host "ai-product-discovery.softdemonew.info"
php bin/magento config:set discovery_suite_config/api/search_port 7001
php bin/magento config:set discovery_suite_config/api/recommendation_host "ai-product-discovery.softdemonew.info"
php bin/magento config:set discovery_suite_config/api/recommendation_port 7002

# Clear cache after configuration
php bin/magento cache:flush
```

## 🧪 PART 3: TESTING & VALIDATION

### Test AI Services Connection
```bash
# Test connection to all AI services
php bin/magento discovery:test:connection

# Test advanced AI features (typo tolerance, NLP, etc.)
php bin/magento discovery:test:advanced-ai
```

### Sync Product Catalog
```bash
# Sync all products to AI backend
php bin/magento discovery:sync:catalog
```

### Test Autocomplete Endpoints
```bash
# Test original autocomplete (should work now)
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=hero&limit=10"

# Test typo tolerance (should find "Hero Hoodie" when searching "Hro Hoodie")
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=Hro%20Hoodie&limit=10"

# Test tank products
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=tank&limit=10"

# Test advanced autocomplete
curl "https://magento-test.softdemonew.info/discoverysuite/search/autocompleteadvanced?q=tank&limit=10"
```

## 🔧 PART 4: TROUBLESHOOTING

### Check Service Status
```bash
# Check if AI services are running
ps aux | grep uvicorn
netstat -tlnp | grep 700

# Check AI service logs
tail -f /path/to/ai-product-discovery/search-service.log
tail -f /path/to/ai-product-discovery/recommendation-service.log
```

### Check Magento Integration
```bash
# Check Magento logs
tail -f var/log/system.log
tail -f var/log/exception.log

# Check module status
php bin/magento module:status Vendor_DiscoverySuite

# Debug specific configuration
php bin/magento config:show discovery_suite_config
```

### Fix Common Issues
```bash
# If compilation fails
php bin/magento setup:upgrade
php bin/magento setup:di:compile

# If cache issues persist
php bin/magento cache:clean config
php bin/magento cache:clean layout
php bin/magento cache:clean block_html

# Reset permissions if needed
find . -type f -exec chmod 644 {} \;
find . -type d -exec chmod 755 {} \;
chmod -R 777 var/ pub/static/ pub/media/
```

## 🎯 PART 5: EXPECTED RESULTS

After successful deployment, these should work:

### 1. Typo Tolerance Working ✅
```bash
# "Hro Hoodie" should return "Hero Hoodie" results
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=Hro%20Hoodie&limit=10"
```

### 2. Proper Response Format ✅
```json
{
  "success": true,
  "query": "Hro Hoodie",
  "suggestions": [
    {
      "title": "Hero Hoodie",
      "image": "https://example.com/images/hero-hoodie.jpg",
      "price": "$59.99",
      "url": "/hero-hoodie",
      "category": "Hoodies",
      "is_corrected": true,
      "correction_confidence": 0.9
    }
  ],
  "correction_message": "Showing results for \"Hero Hoodie\" (corrected from \"Hro Hoodie\")",
  "has_corrections": true
}
```

### 3. All AI Features Active ✅
- NLP semantic search
- Typo tolerance & auto-correct
- Intent recognition  
- ML-powered recommendations
- Real-time learning
- Conversational AI assistant

## 📞 Support

If any step fails, check:
1. AI services are running on ports 7001-7004
2. Magento module is properly compiled
3. Configuration values are set correctly
4. Network connectivity between services