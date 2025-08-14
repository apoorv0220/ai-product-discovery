# 🚀 Production Deployment Guide - AI Search Service

## Overview
This guide provides step-by-step instructions to deploy the enhanced AI search service with OpenAI integration to your production server.

## 📋 Prerequisites

### 1. Server Requirements
- **AI Server**: `ai-product-discovery.softdemonew.info`
- **Python 3.9+** installed
- **Redis server** running
- **OpenAI API Key** (required for enhanced search)

### 2. Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key (starts with `sk-...`)

---

## 🔧 Step 1: Prepare Files for Upload

### Files to Upload to Server:
```bash
# Updated backend files
backend/search-service/core/openai_nlp.py          # ← NEW OpenAI integration
backend/search-service/api/autocomplete.py         # ← Enhanced with OpenAI
backend/requirements.txt                           # ← Updated dependencies

# Deployment scripts
deploy_search_fixes.sh                             # ← Deployment script
test_search_fixes.sh                              # ← Testing script
```

---

## 🚀 Step 2: Deploy to Production Server

### 2.1 Upload Files to Server
```bash
# Option A: Using SCP (recommended)
scp -r backend/ root@ai-product-discovery.softdemonew.info:/path/to/ai-product-discovery/
scp deploy_search_fixes.sh root@ai-product-discovery.softdemonew.info:/path/to/ai-product-discovery/
scp test_search_fixes.sh root@ai-product-discovery.softdemonew.info:/path/to/ai-product-discovery/

# Option B: Using rsync
rsync -avz backend/ root@ai-product-discovery.softdemonew.info:/path/to/ai-product-discovery/backend/
```

### 2.2 SSH into Production Server
```bash
ssh root@ai-product-discovery.softdemonew.info
cd /path/to/ai-product-discovery
```

---

## ⚙️ Step 3: Configure Environment

### 3.1 Set OpenAI API Key
```bash
# Set environment variable (replace with your actual API key)
export OPENAI_API_KEY="sk-your-actual-openai-api-key-here"

# Make it permanent by adding to ~/.bashrc or ~/.profile
echo 'export OPENAI_API_KEY="sk-your-actual-openai-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 3.2 Install/Update Dependencies
```bash
# Create virtual environment if not exists
python3 -m venv venv
source venv/bin/activate

# Install updated requirements
pip install -r backend/requirements.txt

# Specifically install the new dependency
pip install httpx==0.28.1
```

---

## 🔄 Step 4: Deploy Search Service

### 4.1 Stop Current Search Service
```bash
# Find and stop the current search service
pkill -f "search-service.*7001"

# Or if you have the PID
# kill <PID>
```

### 4.2 Start Enhanced Search Service
```bash
# Navigate to backend directory
cd backend

# Start search service with OpenAI integration
nohup python3 -m uvicorn search-service.main:app \
    --host 0.0.0.0 \
    --port 7001 \
    --reload > ../search-service.log 2>&1 &

# Note the new PID
echo $! > ../search-service.pid
```

### 4.3 Verify Service is Running
```bash
# Check if service is responding
curl http://localhost:7001/health

# Check logs for any errors
tail -f ../search-service.log
```

---

## 🧪 Step 5: Test Enhanced Search

### 5.1 Test OpenAI Integration
```bash
# Test typo correction: "Hro Hoodie" should find "Hero Hoodie"
curl "http://localhost:7001/api/v1/autocomplete/?q=Hro%20Hoodie&limit=5" | python3 -m json.tool

# Test semantic search: Natural language query
curl "http://localhost:7001/api/v1/autocomplete/?q=I%20want%20to%20buy%20a%20comfortable%20hoodie&limit=5" | python3 -m json.tool

# Test regular search still works
curl "http://localhost:7001/api/v1/autocomplete/?q=hero&limit=5" | python3 -m json.tool
```

### 5.2 Test Magento Integration
```bash
# Test the Magento endpoints
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=Hro%20Hoodie&limit=5" | python3 -m json.tool

curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=I%20want%20to%20buy%20a%20comfortable%20hoodie&limit=5" | python3 -m json.tool
```

### 5.3 Run Comprehensive Test
```bash
# Use the test script
chmod +x test_search_fixes.sh
./test_search_fixes.sh
```

---

## 📊 Step 6: Monitor and Verify

### 6.1 Check Service Logs
```bash
# Monitor real-time logs
tail -f search-service.log

# Look for OpenAI API calls
grep -i "openai" search-service.log

# Check for errors
grep -i "error" search-service.log
```

### 6.2 Test Advanced Features

#### ✅ Expected Results:

**1. Typo Correction:**
```bash
# Query: "Hro Hoodie"
# Should return: Hero Hoodie products with typo correction metadata
```

**2. Semantic Search:**
```bash
# Query: "I want to buy a comfortable hoodie"
# Should return: Hoodie products, extracting "comfortable hoodie" as key terms
```

**3. Enhanced Data:**
```bash
# Should show:
# - Proper category names (not IDs)
# - Real prices (not $0.00)
# - Better image URLs (not placeholders)
```

---

## 🔧 Step 7: Troubleshooting

### 7.1 Common Issues

**Issue: OpenAI API Key Not Working**
```bash
# Check if key is set
echo $OPENAI_API_KEY

# Test API key directly
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

**Issue: Service Not Starting**
```bash
# Check Python path
which python3

# Check if port is in use
netstat -tlnp | grep 7001

# Check detailed logs
cat search-service.log
```

**Issue: No Search Results**
```bash
# Check if products are indexed
curl "http://localhost:7001/api/v1/index/status"

# Re-sync products if needed (from Magento server)
php bin/magento discovery:sync:catalog
```

### 7.2 Fallback Mode
If OpenAI is not working, the service will automatically fall back to basic search with simple typo correction.

---

## 🎯 Step 8: Final Verification

### 8.1 Test All Search Scenarios
```bash
# 1. Exact match
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=hero"

# 2. Typo correction
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=Hro%20Hoodie"

# 3. Semantic search
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=I%20want%20comfortable%20clothing"

# 4. Natural language
curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=best%20running%20shoes%20for%20men"
```

### 8.2 Performance Check
```bash
# Monitor response times
time curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=Hro%20Hoodie"

# Check OpenAI API usage (should be fast, <2 seconds)
```

---

## 🎉 Success Criteria

✅ **Typo Correction Works**: "Hro Hoodie" returns "Hero Hoodie" results  
✅ **Semantic Search Works**: Natural language queries return relevant products  
✅ **Categories Display Names**: Shows "Hoodies & Sweatshirts" not "15"  
✅ **Prices Display Correctly**: Shows actual prices, not "$0.00"  
✅ **Images Work**: No placeholder images  
✅ **Performance**: Response time < 2 seconds  
✅ **Fallback Works**: Service works even if OpenAI fails  

---

## 📞 Support Commands

```bash
# Restart search service
pkill -f "search-service.*7001"
cd /path/to/ai-product-discovery/backend
nohup python3 -m uvicorn search-service.main:app --host 0.0.0.0 --port 7001 > ../search-service.log 2>&1 &

# Check all AI services status
curl http://localhost:7001/health  # Search
curl http://localhost:7002/health  # Recommendations  
curl http://localhost:7003/health  # Analytics
curl http://localhost:7004/health  # Assistant

# View live logs
tail -f search-service.log
```

---

**🎯 This deployment will give you:**
- **100% working typo correction** using OpenAI
- **Advanced semantic search** for natural language
- **Proper product data display** (categories, prices, images)
- **Fallback protection** if OpenAI is unavailable
- **Production-ready performance** with monitoring
