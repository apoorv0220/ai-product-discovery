# 🏠 Localhost Quick Start Guide

**AI Product Discovery Suite** - Run and verify everything on your localhost in 3 simple steps!

## ⚡ Quick Start (3 Commands)

```bash
# 1. Start all services (takes ~3 minutes)
./quick_start.sh

# 2. Test all APIs (takes ~1 minute)
./test_apis.sh

# 3. Run comprehensive verification (optional)
python scripts/verify_localhost.py
```

That's it! 🎉 Your AI Product Discovery Suite is now running with dummy data.

---

## 🎯 What You Get

### ✅ **Running Services**
- **Search API** - AI-powered product search with intelligent ranking
- **Recommendations API** - ML-based personalized product recommendations  
- **Analytics API** - Real-time event tracking and user behavior analysis
- **Shopping Assistant API** - Conversational AI for customer support

### 📊 **Dummy Data Included**
- **8 Product Categories** (Electronics, Laptops, Smartphones, etc.)
- **10 Sample Products** (MacBook Pro, iPhone 15, PlayStation 5, etc.)
- **5 Test Users** with different preferences and budgets
- **Sample Search Queries** and analytics events
- **Recommendation Logs** with various contexts

### 🌐 **Demo Pages** 
- **Search Demo**: `demo/search.html` - Interactive product search
- **Recommendations Demo**: `demo/recommendations.html` - Personalized recommendations

---

## 🔧 Manual Testing

### Quick API Tests
```bash
# Search for products
curl -X POST http://localhost:8001/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "MacBook", "limit": 5}'

# Get recommendations
curl -X POST http://localhost:8002/api/v1/recommendations/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": "1", "context": "home", "limit": 8}'

# Track an event
curl -X POST http://localhost:8004/api/v1/events/track \
  -H "Content-Type: application/json" \
  -d '{"event_type": "product_view", "user_id": "1", "properties": {"product_id": "1"}}'

# Chat with assistant
curl -X POST http://localhost:8005/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test", "message": "I need a laptop for programming"}'
```

### View Demo Pages
```bash
# Open in browser
open demo/search.html
open demo/recommendations.html

# Or start local server
cd demo && python -m http.server 3000
# Then visit: http://localhost:3000/search.html
```

---

## 🎭 Example Use Cases

### 🔍 **E-commerce Search**
- **Intelligent Search**: "MacBook laptop" → Returns Apple MacBook Pro with high relevance
- **Typo Tolerance**: "Macbok" → Still finds MacBook products
- **Category Filtering**: Search "laptop" with category filter → Only laptops
- **Price Range**: Search with budget filters for targeted results

### 🤖 **Personalized Recommendations**
- **User #1** (John - Electronics enthusiast): Gets high-end tech recommendations
- **User #2** (Jane - Audio lover): Gets headphones and speakers
- **User #3** (Mike - Gamer): Gets gaming consoles and accessories
- **Context-aware**: Homepage vs Product detail vs Cart recommendations

### 📊 **Analytics & Insights**
- **Real-time Tracking**: Product views, cart additions, purchases
- **User Journey**: Complete customer behavior analysis
- **Performance Metrics**: Search response times, click-through rates
- **A/B Testing**: Compare different recommendation algorithms

### 🛍️ **Shopping Assistant**
- **Product Discovery**: "I need a laptop for video editing"
- **Budget Guidance**: "What's the best laptop under $2000?"
- **Comparison**: "Compare MacBook vs Dell XPS"
- **Personalized Help**: Based on user preferences and history

---

## 🌐 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Search API | http://localhost:8001/api/v1/search/ | Product search |
| Recommendations | http://localhost:8002/api/v1/recommendations/ | ML recommendations |
| Analytics | http://localhost:8004/api/v1/events/ | Event tracking |
| Shopping Assistant | http://localhost:8005/api/v1/chat/ | AI chatbot |
| RabbitMQ Management | http://localhost:15672/ | Message queue (guest/guest) |
| Elasticsearch | http://localhost:9200/ | Search engine |
| Weaviate | http://localhost:8080/v1/meta | Vector database |

---

## 🐛 Troubleshooting

### Services Not Starting?
```bash
# Check Docker status
docker-compose ps

# View service logs
docker-compose logs search-service
docker-compose logs recommendation-service

# Restart specific service
docker-compose restart search-service
```

### API Not Responding?
```bash
# Check service health
curl http://localhost:8001/health/
curl http://localhost:8002/health/

# Check if ports are busy
lsof -i :8001,8002,8004,8005
```

### Out of Memory?
```bash
# Check Docker stats
docker stats

# Increase Docker memory in Docker Desktop
# Settings → Resources → Memory → 8GB+
```

### Python Issues?
```bash
# Install dependencies
pip install aiohttp asyncio structlog sqlalchemy

# Or use Python 3
python3 -m pip install aiohttp asyncio
```

---

## 🚀 Next Steps

### 1. **Production Deployment**
Ready for production? Check out `PRODUCTION_DEPLOYMENT_GUIDE.md`

### 2. **Magento Integration**
Want to integrate with Magento? The module is ready in `magento2-module/`

### 3. **Custom Data**
Replace dummy data with your real product catalog:
- Update `scripts/init_dummy_data.py`
- Import your categories and products
- Configure user preferences

### 4. **Advanced Features**
Explore additional AI capabilities:
- Visual search with image recognition
- Voice search with speech-to-text
- Advanced ML recommendation algorithms
- Real-time personalization

---

## 🎊 Success!

If you can see this and the APIs are responding, congratulations! 

You now have a **fully functional AI Product Discovery Suite** running on localhost with:

✅ **Intelligent search** with semantic understanding  
✅ **ML-powered recommendations** with personalization  
✅ **Real-time analytics** with event tracking  
✅ **AI shopping assistant** with natural language processing  
✅ **Complete dummy dataset** for immediate testing  
✅ **Demo pages** for visual verification  

**Happy coding!** 🚀

---

## 📞 Need Help?

- Check the [full documentation](LOCAL_VERIFICATION_GUIDE.md)
- Review [troubleshooting guide](LOCAL_VERIFICATION_GUIDE.md#troubleshooting)
- Run detailed verification: `python scripts/verify_localhost.py`
- Test individual APIs: `./test_apis.sh`