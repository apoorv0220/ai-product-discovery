# 🎯 **FRONTEND MODULE VISIBILITY GUIDE - COMPLETE CONDITIONS ANALYSIS**

## **📋 OVERVIEW**

This guide explains **exactly when and where each AI Discovery Suite frontend module appears**, including all conditions that must be met for visibility.

---

## **🔧 GLOBAL REQUIREMENTS (ALL MODULES)**

### **✅ Basic Prerequisites**
1. **Module Enabled**: `Vendor_DiscoverySuite` module must be enabled
   ```bash
   php bin/magento module:status Vendor_DiscoverySuite
   # Should show: "Module is enabled"
   ```

2. **Main Configuration**: `discovery_suite_config/general/enabled` = `1`
   ```bash
   php bin/magento config:set discovery_suite_config/general/enabled 1
   ```

3. **API Configuration**: Valid `api_base_url` configured
   ```bash
   php bin/magento config:set discovery_suite_config/general/api_base_url "http://ai-product-discovery.softdemonew.info"
   ```

4. **Cache Clear**: All caches must be flushed after configuration changes
   ```bash
   php bin/magento cache:flush
   ```

5. **Static Content**: Must be deployed (for CSS/JS)
   ```bash
   php bin/magento setup:static-content:deploy
   ```

---

## **🔍 SEARCH AUTOCOMPLETE MODULE**

### **📍 Where It Appears**
- **Location**: Top search bar (all pages)
- **Layout**: `default.xml` → `referenceBlock name="top.search"`
- **Template**: `search/autocomplete.phtml`
- **Block**: `Vendor\DiscoverySuite\Block\Search\Autocomplete`

### **✅ Visibility Conditions**
1. **Global Requirements** (above) ✅
2. **Search Enabled**: `discovery_suite_config/search/enabled` = `1`
3. **Autocomplete Enabled**: `discovery_suite_config/search/autocomplete_enabled` = `1`
4. **Block Check**: `$block->isEnabled()` returns `true`

### **🔧 Enable Commands**
```bash
php bin/magento config:set discovery_suite_config/search/enabled 1
php bin/magento config:set discovery_suite_config/search/autocomplete_enabled 1
php bin/magento cache:flush
```

### **🚨 Troubleshooting**
- **Not Visible**: Check if `#search` element exists in DOM
- **No Suggestions**: Verify products are synced (`php bin/magento discovery:sync:catalog`)
- **Empty Results**: Check API connectivity (`php bin/magento discovery:test:connection`)

---

## **📦 PRODUCT RECOMMENDATIONS MODULE**

### **📍 Where It Appears**
- **Product Pages**: Below product details (`catalog_product_view.xml`)
- **Category Pages**: After product list (`catalog_category_view.xml`)
- **Template**: `recommendations/similar-products.phtml` (product) / `recommendations/category-recommendations.phtml` (category)
- **Block**: `Vendor\DiscoverySuite\Block\Recommendations\Widget`

### **✅ Visibility Conditions**
1. **Global Requirements** (above) ✅
2. **Recommendations Enabled**: `discovery_suite_config/recommendations/enabled` = `1`
3. **Page-Specific Enabled**:
   - Product: `discovery_suite_config/recommendations/product_page_enabled` = `1`
   - Category: `discovery_suite_config/recommendations/category_page_enabled` = `1`
4. **Block Check**: `$block->isEnabled()` returns `true`
5. **Data Available**: Must have recommendations data from API

### **🔧 Enable Commands**
```bash
php bin/magento config:set discovery_suite_config/recommendations/enabled 1
php bin/magento config:set discovery_suite_config/recommendations/product_page_enabled 1
php bin/magento config:set discovery_suite_config/recommendations/category_page_enabled 1
php bin/magento cache:flush
```

### **🎯 Product Page Specific**
- **Context**: `product_view`
- **Trigger**: Must be on actual product page with `current_product` in registry
- **API Call**: `/api/v1/recommendations/similar` with product ID

### **🎯 Category Page Specific**
- **Context**: `category_view`
- **Trigger**: Must be on category page with `current_category` in registry
- **API Call**: `/api/v1/recommendations/` with category context

---

## **🛒 SHOPPING ASSISTANT WIDGET**

### **📍 Where It Appears**
- **Location**: Bottom-right corner (all pages)
- **Layout**: `default.xml` → `referenceContainer name="before.body.end"`
- **Template**: `assistant/widget.phtml`
- **Block**: `Vendor\DiscoverySuite\Block\Assistant\Widget`

### **✅ Visibility Conditions**
1. **Global Requirements** (above) ✅
2. **Shopping Assistant Enabled**: `discovery_suite_config/shopping_assistant/enabled` = `1`
3. **Block Check**: `$block->isEnabled()` returns `true`
4. **Position**: Must have valid `widget_position` setting
5. **JavaScript**: Widget requires JavaScript to function

### **🔧 Enable Commands**
```bash
php bin/magento config:set discovery_suite_config/shopping_assistant/enabled 1
php bin/magento config:set discovery_suite_config/shopping_assistant/widget_position "bottom_right"
php bin/magento cache:flush
```

### **🎨 Widget Behavior**
- **Initial State**: Minimized by default
- **Activation**: Click to open chat interface
- **API Endpoint**: `/api/v1/chat/` for conversation

---

## **📊 ANALYTICS TRACKING MODULE**

### **📍 Where It Appears**
- **Location**: Invisible pixel (all pages)
- **Layout**: `default.xml` → `referenceContainer name="before.body.end"`
- **Template**: `analytics/pixel.phtml`
- **Block**: `Vendor\DiscoverySuite\Block\Analytics\Pixel`

### **✅ Visibility Conditions**
1. **Global Requirements** (above) ✅
2. **Analytics Enabled**: `discovery_suite_config/analytics/enabled` = `1`
3. **Block Check**: `$block->isEnabled()` returns `true`

### **🔧 Enable Commands**
```bash
php bin/magento config:set discovery_suite_config/analytics/enabled 1
php bin/magento cache:flush
```

### **🔍 Detection**
- **Visual**: Invisible `div` element with `id="discovery-analytics-pixel"`
- **JavaScript**: `discoveryAnalytics` object initialized
- **Tracking**: Events sent to `/api/v1/events/`

---

## **📂 DYNAMIC FILTERS MODULE**

### **📍 Where It Appears**
- **Location**: Left sidebar on category pages
- **Layout**: `catalog_category_view.xml` → `referenceContainer name="catalog.leftnav"`
- **Template**: `listing/dynamic-filters.phtml`
- **Block**: `Vendor\DiscoverySuite\Block\Listing\DynamicFilters`

### **✅ Visibility Conditions**
1. **Global Requirements** (above) ✅
2. **Smart Listings Enabled**: `discovery_suite_config/smart_listings/enabled` = `1`
3. **Dynamic Filters Enabled**: `discovery_suite_config/smart_listings/dynamic_filters_enabled` = `1`
4. **Category Page**: Must be on category page with `current_category` in registry
5. **Block Check**: `$block->isEnabled()` AND `$listingOptimizer->isEnabled()` = `true`

### **🔧 Enable Commands**
```bash
php bin/magento config:set discovery_suite_config/smart_listings/enabled 1
php bin/magento config:set discovery_suite_config/smart_listings/dynamic_filters_enabled 1
php bin/magento cache:flush
```

---

## **⚙️ COMPLETE CONFIGURATION CHECKLIST**

### **🎯 Quick Setup - All Features Enabled**
```bash
# Main module
php bin/magento config:set discovery_suite_config/general/enabled 1
php bin/magento config:set discovery_suite_config/general/api_base_url "http://ai-product-discovery.softdemonew.info"

# Search & Autocomplete
php bin/magento config:set discovery_suite_config/search/enabled 1
php bin/magento config:set discovery_suite_config/search/autocomplete_enabled 1

# Recommendations
php bin/magento config:set discovery_suite_config/recommendations/enabled 1
php bin/magento config:set discovery_suite_config/recommendations/product_page_enabled 1
php bin/magento config:set discovery_suite_config/recommendations/category_page_enabled 1
php bin/magento config:set discovery_suite_config/recommendations/cart_page_enabled 1

# Smart Listings
php bin/magento config:set discovery_suite_config/smart_listings/enabled 1
php bin/magento config:set discovery_suite_config/smart_listings/auto_sort_enabled 1
php bin/magento config:set discovery_suite_config/smart_listings/dynamic_filters_enabled 1

# Shopping Assistant
php bin/magento config:set discovery_suite_config/shopping_assistant/enabled 1
php bin/magento config:set discovery_suite_config/shopping_assistant/widget_position "bottom_right"

# Analytics
php bin/magento config:set discovery_suite_config/analytics/enabled 1

# Final steps
php bin/magento cache:flush
php bin/magento setup:static-content:deploy -f
```

---

## **🔍 DEBUGGING - MODULE NOT VISIBLE**

### **Step 1: Basic Checks**
```bash
# Module status
php bin/magento module:status Vendor_DiscoverySuite

# Main configuration
php bin/magento config:show discovery_suite_config/general/enabled

# Specific feature (example: recommendations)
php bin/magento config:show discovery_suite_config/recommendations/enabled
```

### **Step 2: API Connectivity**
```bash
# Test all services
php bin/magento discovery:test:connection

# Expected output: All services show "Connected" status
```

### **Step 3: Data Availability**
```bash
# Sync products from Magento to AI services
php bin/magento discovery:sync:catalog

# Expected: "Synced X products" where X > 0
```

### **Step 4: Frontend Inspection**
1. **View Page Source**: Look for block HTML elements
2. **Browser Console**: Check for JavaScript errors (F12)
3. **Network Tab**: Verify API calls are being made
4. **Elements Tab**: Look for expected CSS classes and IDs

### **Step 5: Layout Debugging**
```bash
# Enable template hints (developer mode)
php bin/magento deploy:mode:set developer
php bin/magento dev:template-hints:enable

# Check layout rendering
```

---

## **🎯 SPECIFIC PAGE TESTING**

### **🏠 Homepage Testing**
**Should Show**:
- ✅ Search autocomplete in header
- ✅ Shopping assistant widget (bottom-right)
- ✅ Analytics tracking (invisible)

**Test URLs**:
- Base URL: `https://magento-test.softdemonew.info/`

### **📦 Product Page Testing**
**Should Show**:
- ✅ Search autocomplete in header
- ✅ Similar products section (below product details)
- ✅ Shopping assistant widget (bottom-right)
- ✅ Analytics tracking (invisible)

**Test URLs**:
- Any product: `https://magento-test.softdemonew.info/product-name.html`

### **📂 Category Page Testing**
**Should Show**:
- ✅ Search autocomplete in header
- ✅ Dynamic filters (left sidebar)
- ✅ Category recommendations (after product list)
- ✅ Shopping assistant widget (bottom-right)
- ✅ Analytics tracking (invisible)

**Test URLs**:
- Any category: `https://magento-test.softdemonew.info/category-name.html`

---

## **🚨 COMMON ISSUES & SOLUTIONS**

### **Issue: "Module appears enabled but not visible"**
**Solution**:
1. Clear all caches: `php bin/magento cache:flush`
2. Recompile: `php bin/magento setup:di:compile`
3. Deploy static: `php bin/magento setup:static-content:deploy -f`

### **Issue: "JavaScript console errors"**
**Solution**:
1. Check RequireJS config in browser
2. Verify static files deployed properly
3. Clear browser cache

### **Issue: "API calls failing"**
**Solution**:
1. Test connectivity: `php bin/magento discovery:test:connection`
2. Check AI services status: `docker-compose ps`
3. Verify network between Magento and AI servers

### **Issue: "Empty recommendations/autocomplete"**
**Solution**:
1. Sync products: `php bin/magento discovery:sync:catalog`
2. Check product count: `curl http://ai-product-discovery.softdemonew.info:7001/api/v1/index/status`
3. Verify product visibility settings in Magento

---

## **✅ SUCCESS VERIFICATION CHECKLIST**

### **After Complete Setup, You Should See**:

#### **✅ All Pages**:
- [ ] Search autocomplete dropdown when typing in header search
- [ ] Shopping assistant icon in bottom-right corner
- [ ] No JavaScript errors in console (F12)

#### **✅ Product Pages**:
- [ ] "You Might Also Like" or similar products section
- [ ] Real product data (not "product_1", "product_2" dummy data)
- [ ] Clicking products navigates to correct pages

#### **✅ Category Pages**:
- [ ] AI-enhanced filters in left sidebar
- [ ] Recommendation widgets showing relevant products
- [ ] Smart sorting options in product toolbar

#### **✅ Technical Verification**:
- [ ] All config values return `1`: `php bin/magento config:show discovery_suite_config/general/enabled`
- [ ] Connection test passes: `php bin/magento discovery:test:connection`
- [ ] Products synced: `php bin/magento discovery:sync:catalog` shows count > 0
- [ ] APIs return real data: `curl "https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=test"`

**If all checkboxes are ✅, your AI Product Discovery Suite is fully functional!**

---

## **📞 SUPPORT REFERENCE**

### **Key Commands**:
```bash
# Module status
php bin/magento module:status Vendor_DiscoverySuite

# Test connectivity  
php bin/magento discovery:test:connection

# Sync products
php bin/magento discovery:sync:catalog

# View all configuration
php bin/magento config:show | grep discovery_suite_config

# Clear everything
php bin/magento cache:flush && php bin/magento setup:di:compile
```

### **Key URLs for Testing**:
- Autocomplete API: `https://magento-test.softdemonew.info/discovery/search/autocomplete/?q=test`
- AI Services Health: `http://ai-product-discovery.softdemonew.info:7001/health/`
- Admin Configuration: `Stores → Configuration → AI Discovery Suite`
