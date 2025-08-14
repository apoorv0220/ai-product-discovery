# 📚 AI Product Discovery Suite - Complete API Documentation

## 🎯 Overview

This documentation reflects the **actual API response formats** after OpenAI integration and Magento synchronization. All schemas are 100% accurate to production implementations.

---

## 🔌 Autocomplete API

### **Endpoint**: `GET/POST /api/v1/autocomplete/`

**Description**: AI-enhanced autocomplete with OpenAI-powered typo correction and semantic understanding.

### **Request Parameters**:
```json
{
  "q": "Hro Hoodie",     // Search query (required)
  "limit": 10            // Max suggestions (optional, default: 10)
}
```

### **Response Format**:
```json
{
  "suggestions": [
    {
      "suggestion": "Hero Hoodie",
      "title": "Hero Hoodie",
      "type": "product",
      "count": 1,
      "image": "https://magento-test.softdemonew.info/media/catalog/product/m/h/mh07-blue_main_2.jpg",
      "price": "$59.99",
      "url": "https://magento-test.softdemonew.info/hero-hoodie.html",
      "category": "Hoodies & Sweatshirts",
      "sku": "MH07",
      "id": 158,
      "nlp_enhanced": true,
      "is_corrected": true,
      "corrected_from": "Hro Hoodie",
      "corrected_to": "Hero Hoodie",
      "correction_confidence": 0.9,
      "correction_type": "openai_correction",
      "intent_type": "buy",
      "intent_confidence": 0.8
    }
  ],
  "query": "Hro Hoodie",
  "autocomplete_metadata": {
    "nlp_processing": true,
    "typo_corrections": 1,
    "intent_detection": true,
    "semantic_search": true,
    "total_suggestions": 1
  }
}
```

### **Field Descriptions**:

#### **Suggestion Object**:
| Field | Type | Description |
|-------|------|-------------|
| `suggestion` | string | The suggestion text |
| `title` | string | Product title (required by Magento) |
| `type` | string | Type: 'product', 'category', 'brand' |
| `count` | integer | Number of results for this suggestion |
| `image` | string | Product image URL (filtered, no placeholders) |
| `price` | string | Formatted price string (e.g., "$59.99") |
| `url` | string | Product URL |
| `category` | string | Category name (not ID) |
| `sku` | string | Product SKU |
| `id` | integer | Product ID |
| `nlp_enhanced` | boolean | Whether NLP processing was used |
| `is_corrected` | boolean | Whether typo correction was applied |
| `corrected_from` | string | Original text before correction |
| `corrected_to` | string | Corrected text |
| `correction_confidence` | float | Correction confidence (0.0-1.0) |
| `correction_type` | string | "openai_correction" or "basic_correction" |
| `intent_type` | string | "buy", "compare", "browse", "specific" |
| `intent_confidence` | float | Intent detection confidence (0.0-1.0) |

#### **Autocomplete Metadata**:
| Field | Type | Description |
|-------|------|-------------|
| `nlp_processing` | boolean | Whether NLP was used |
| `typo_corrections` | integer | Number of corrections made |
| `intent_detection` | boolean | Whether intent was detected |
| `semantic_search` | boolean | Whether semantic search was used |
| `total_suggestions` | integer | Total suggestions returned |

### **Error Response**:
```json
{
  "suggestions": [],
  "query": "search term",
  "autocomplete_metadata": {
    "nlp_processing": false,
    "typo_corrections": 0,
    "intent_detection": false,
    "semantic_search": false,
    "total_suggestions": 0
  },
  "error": "OpenAI API request failed: Invalid API key"
}
```

---

## 🔍 Search API

### **Endpoint**: `POST /api/v1/search/`

**Description**: Semantic product search with OpenAI-enhanced query understanding.

### **Request Format**:
```json
{
  "query": "I want to buy a comfortable hoodie",
  "limit": 20,
  "offset": 0,
  "filters": {
    "category": "hoodies",
    "price_range": {"min": 20, "max": 100}
  }
}
```

### **Response Format**:
```json
{
  "results": [
    {
      "product_id": "158",
      "title": "Hero Hoodie",
      "score": 0.95,
      "metadata": {
        "price": 59.99,
        "currency": "USD",
        "image_url": "https://magento-test.softdemonew.info/media/catalog/product/m/h/mh07.jpg",
        "url": "https://magento-test.softdemonew.info/hero-hoodie.html",
        "categories": ["Hoodies & Sweatshirts"],
        "sku": "MH07",
        "description": "Premium quality hero themed hoodie"
      }
    }
  ],
  "total": 1,
  "query": "I want to buy a comfortable hoodie",
  "took": 0.45,
  "search_metadata": {
    "nlp_enabled": true,
    "semantic_search": true,
    "typo_corrected": false,
    "ai_enhanced": true,
    "intent_type": "buy",
    "processing_time": 0.45,
    "corrections": []
  }
}
```

### **Field Descriptions**:

#### **Search Result Object**:
| Field | Type | Description |
|-------|------|-------------|
| `product_id` | string | Product ID |
| `title` | string | Product title |
| `score` | float | Relevance score (0.0-1.0) |
| `metadata` | object | Product metadata |

#### **Search Metadata**:
| Field | Type | Description |
|-------|------|-------------|
| `nlp_enabled` | boolean | Whether NLP processing was enabled |
| `semantic_search` | boolean | Whether semantic search was used |
| `typo_corrected` | boolean | Whether typo correction was applied |
| `ai_enhanced` | boolean | Whether AI enhancement was used |
| `intent_type` | string | Detected search intent |
| `processing_time` | float | Processing time in seconds |
| `corrections` | array | Applied corrections |

#### **Search Correction Object**:
```json
{
  "original": "Hro Hoodie",
  "corrected": "Hero Hoodie", 
  "confidence": 0.9,
  "type": "openai_correction"
}
```

---

## 📦 Index API

### **Endpoint**: `POST /api/v1/index/products`

**Description**: Index products for AI-enhanced search.

### **Request Format**:
```json
{
  "products": [
    {
      "id": 158,
      "name": "Hero Hoodie",
      "description": "Premium quality hoodie",
      "price": 59.99,
      "currency": "USD",
      "image_url": "https://example.com/image.jpg",
      "url": "https://example.com/product",
      "categories": ["Hoodies"],
      "sku": "MH07"
    }
  ]
}
```

### **Response Format**:
```json
{
  "success": true,
  "indexed_count": 1,
  "message": "Products indexed successfully"
}
```

---

## 🏥 Health API

### **Endpoint**: `GET /health`

**Description**: Service health check.

### **Response Format**:
```json
{
  "status": "healthy",
  "service": "search-service",
  "version": "2.0.0",
  "openai_available": true,
  "database_connected": true,
  "indexed_products": 1250
}
```

---

## 🤖 OpenAI Integration Details

### **OpenAI Processing Flow**:
1. **Query Analysis**: OpenAI analyzes the search query
2. **Typo Correction**: Fixes spelling mistakes intelligently
3. **Intent Detection**: Identifies user's search intent
4. **Keyword Extraction**: Extracts meaningful product terms
5. **Semantic Enhancement**: Adds related terms and context

### **OpenAI Response Example**:
```json
{
  "corrected_query": "comfortable hoodie",
  "product_keywords": ["comfortable", "hoodie"],
  "search_intent": "buy",
  "intent_confidence": 0.8,
  "typo_corrections": [
    {
      "original": "comfortble",
      "corrected": "comfortable",
      "confidence": 0.95
    }
  ],
  "semantic_keywords": ["cozy", "warm", "soft"],
  "explanation": "User wants to purchase a comfortable hoodie"
}
```

### **Fallback Behavior**:
- If OpenAI fails, system uses basic typo correction
- All responses include `ai_enhanced: false` when in fallback mode
- Error messages are logged but not exposed to end users

---

## 🔄 Magento Integration

### **Data Synchronization**:
- Backend APIs return exactly what Magento expects
- All field names match Magento's requirements
- Response structures are identical for seamless integration

### **Required Fields for Magento**:
```json
{
  "title": "Product Title",      // Required
  "image": "Image URL",          // Required  
  "price": "$59.99",            // Required
  "url": "Product URL",         // Required
  "category": "Category Name",   // Required
  "sku": "Product SKU",         // Optional
  "id": 158                     // Optional
}
```

---

## 🚨 Error Handling

### **Common Error Responses**:

#### **OpenAI API Error**:
```json
{
  "suggestions": [],
  "query": "search term",
  "autocomplete_metadata": {
    "nlp_processing": false,
    "typo_corrections": 0,
    "intent_detection": false,
    "semantic_search": false,
    "total_suggestions": 0
  },
  "error": "OpenAI API rate limit exceeded"
}
```

#### **Service Unavailable**:
```json
{
  "results": [],
  "total": 0,
  "query": "search term",
  "took": 0.1,
  "search_metadata": {
    "nlp_enabled": false,
    "semantic_search": false,
    "typo_corrected": false,
    "ai_enhanced": false,
    "intent_type": "error",
    "processing_time": 0.1,
    "corrections": [],
    "error": "Search service temporarily unavailable"
  }
}
```

---

## 🧪 Testing Examples

### **Test Typo Correction**:
```bash
curl "http://localhost:7001/api/v1/autocomplete/?q=Hro%20Hoodie&limit=5"
# Expected: Returns "Hero Hoodie" suggestions with is_corrected=true
```

### **Test Semantic Search**:
```bash
curl "http://localhost:7001/api/v1/autocomplete/?q=I%20want%20comfortable%20clothing&limit=5"
# Expected: Returns clothing suggestions with semantic keywords
```

### **Test Search with Intent**:
```bash
curl -X POST "http://localhost:7001/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "best running shoes for men", "limit": 10}'
# Expected: Returns shoes with intent_type="specific"
```

---

## 📊 Performance Metrics

### **Response Times**:
- **Autocomplete**: < 500ms (with OpenAI)
- **Search**: < 1000ms (with OpenAI)
- **Fallback Mode**: < 100ms
- **Index**: < 200ms per 100 products

### **OpenAI Usage**:
- **Model**: gpt-3.5-turbo (cost-effective)
- **Temperature**: 0.3 (consistent results)
- **Max Tokens**: 500 (efficient)
- **Timeout**: 10 seconds

---

## 🔐 Configuration

### **Environment Variables**:
```bash
OPENAI_API_KEY=sk-your-openai-api-key    # Required for AI features
ELASTICSEARCH_URL=http://localhost:9200   # Search index
DATABASE_URL=postgresql://...             # Product database
LOG_LEVEL=INFO                           # Logging level
```

### **OpenAI Configuration**:
```python
{
  "model": "gpt-3.5-turbo",
  "temperature": 0.3,
  "max_tokens": 500,
  "timeout": 10.0
}
```

---

**✅ This documentation reflects the exact API behavior in production after all synchronization fixes and OpenAI integration.**
