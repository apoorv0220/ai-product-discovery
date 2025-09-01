/**
 * Product Interaction Tracking for Personalized Search
 * Tracks user behavior to boost products in search results
 */

define([
    'jquery',
    'mage/storage',
    'Magento_Customer/js/customer-data',
    'Vendor_DiscoverySuite/js/utils/session'
], function ($, storage, customerData, sessionUtils) {
    'use strict';

    $.widget('discovery.productTracking', {
        options: {
            apiEndpoint: '/discovery/interactions/track',
            searchEndpoint: '/discovery/search/track',
            userId: 'anonymous',
            sessionId: ''
        },

        _create: function () {
            this._initTracking();
        },

        _initTracking: function () {
            var self = this;
            
            // Initialize tracking based on page type
            if (window.location.pathname.includes('/product/') || 
                window.location.pathname.match(/\.html$/)) {
                this._initProductPageTracking();
            } else if (window.location.pathname.includes('/catalogsearch/result/')) {
                this._initSearchTracking();
            } else if (window.location.pathname.includes('/catalog/category/')) {
                this._initCategoryTracking();
            }
            
            // Track page views for all pages
            this._trackPageView();
        },
        
        // Track product view
        _trackProductView: function(productData) {
            if (!productData || !productData.id) {
                return;
            }
            
            var trackingData = {
                user_id: sessionUtils.getUserId(),
                session_id: sessionUtils.getSessionId(),
                product_id: productData.id.toString(),
                product_name: productData.name || '',
                product_sku: productData.sku || '',
                categories: productData.categories || [],
                came_from_search: this._isFromSearch(),
                search_query: this._getSearchQuery()
            };
            
            // Send to backend API
            $.ajax({
                url: 'http://localhost:7001/api/v1/tracking/product-view',
                type: 'POST',
                data: JSON.stringify(trackingData),
                contentType: 'application/json',
                success: function(response) {
                    console.log('✅ Product view tracked:', response);
                },
                error: function(xhr, status, error) {
                    console.warn('❌ Failed to track product view:', error);
                }
            });
        },
        
        // Check if user came from search
        _isFromSearch: function() {
            var referrer = document.referrer || '';
            var searchParams = new URLSearchParams(window.location.search);
            return referrer.includes('/catalogsearch/result/') || 
                   searchParams.has('q') || 
                   sessionStorage.getItem('came_from_search') === 'true';
        },
        
        // Get search query if came from search
        _getSearchQuery: function() {
            var searchParams = new URLSearchParams(window.location.search);
            var query = searchParams.get('q') || sessionStorage.getItem('last_search_query');
            
            // Clear the flag after getting it
            sessionStorage.removeItem('came_from_search');
            
            return query;
        },
        
        // Track search query
        self.trackSearchQuery = function(query, results) {
            if (!query || !results) {
                return;
            }
            
            var trackingData = {
                user_id: self.userId,
                query: query,
                results: results.map(function(result) {
                    return result.id || result.product_id || result.sku || '';
                }),
                session_id: self.sessionId
            };
            
            // Send to backend API
            $.ajax({
                url: self.apiEndpoint + '/search-query',
                type: 'POST',
                data: JSON.stringify(trackingData),
                contentType: 'application/json',
                success: function(response) {
                    console.log('Search query tracked:', response);
                },
                error: function(xhr, status, error) {
                    console.warn('Failed to track search query:', error);
                }
            });
        };
        
        // Initialize tracking on product page
        _initProductPageTracking: function() {
            var self = this;
            // Get product data from page or extract from DOM
            var productData = this._extractProductData();
            
            if (productData.id) {
                // Track initial page load
                this._trackProductView(productData);
                
                // Track if user stays on page for more than 10 seconds
                setTimeout(function() {
                    self._trackProductView(productData);
                }, 10000);
            }
        },
        
        // Extract product data from page
        self.extractProductData = function() {
            var productData = window.productData || {};
            
            // If no global product data, try to extract from DOM
            if (!productData.id) {
                // Try different selectors for product ID
                var productId = $('input[name="product"]').val() ||
                               $('[data-product-id]').first().data('product-id') ||
                               $('body').data('product-id');
                
                if (productId) {
                    productData.id = productId;
                    
                    // Try to get product name
                    productData.name = $('.page-title .base').text().trim() ||
                                     $('h1.product-name').text().trim() ||
                                     $('[data-product-name]').first().data('product-name') ||
                                     document.title.split(' - ')[0];
                    
                    // Try to get SKU
                    productData.sku = $('.product-info-main [data-th="SKU"]').text().trim() ||
                                    $('[data-product-sku]').first().data('product-sku');
                    
                    // Try to get categories from breadcrumbs
                    var categories = [];
                    $('.breadcrumbs .item').each(function() {
                        var categoryName = $(this).find('a').text().trim();
                        if (categoryName && categoryName !== 'Home') {
                            categories.push(categoryName);
                        }
                    });
                    productData.categories = categories;
                }
            }
            
            return productData;
        };
        
        // Initialize tracking on search results page
        self.initSearchTracking = function() {
            var searchQuery = $('input[name="q"]').val() || '';
            var searchResults = [];
            
            // Extract product IDs from search results
            $('.product-item').each(function() {
                var productId = $(this).data('product-id') || 
                               $(this).find('[data-product-id]').data('product-id') ||
                               $(this).find('.product-item-link').attr('href').match(/\/id\/(\d+)/)?.[1];
                
                if (productId) {
                    searchResults.push({
                        id: productId,
                        name: $(this).find('.product-item-link').text().trim()
                    });
                }
            });
            
            if (searchQuery && searchResults.length > 0) {
                self.trackSearchQuery(searchQuery, searchResults);
            }
        };
        
        // Initialize tracking on catalog/category pages
        self.initCategoryTracking = function() {
            var categoryId = $('body').data('category-id') || 
                            window.location.pathname.match(/\/category\/(\d+)/)?.[1];
            
            if (categoryId) {
                // Track category view
                var categoryData = {
                    user_id: self.userId,
                    category_id: categoryId,
                    session_id: self.sessionId
                };
                
                $.ajax({
                    url: self.apiEndpoint + '/category-view',
                    type: 'POST',
                    data: JSON.stringify(categoryData),
                    contentType: 'application/json'
                });
            }
        };
        
        // Initialize all tracking
        self.init = function() {
            // Initialize based on page type
            if (window.location.pathname.includes('/product/')) {
                self.initProductPageTracking();
            } else if (window.location.pathname.includes('/catalogsearch/result/')) {
                self.initSearchTracking();
            } else if (window.location.pathname.includes('/catalog/category/')) {
                self.initCategoryTracking();
            }
            
            // Track page views for all pages
            self.trackPageView();
        };
        
        // Track page view
        self.trackPageView = function() {
            var pageData = {
                user_id: self.userId,
                page_url: window.location.href,
                page_title: document.title,
                session_id: self.sessionId,
                timestamp: new Date().toISOString()
            };
            
            $.ajax({
                url: self.apiEndpoint + '/page-view',
                type: 'POST',
                data: JSON.stringify(pageData),
                contentType: 'application/json'
            });
        };
        
        // Initialize when DOM is ready
        $(document).ready(function() {
            self.init();
        });
        
        // Expose methods for external use
        window.discoveryProductTracking = {
            trackProductView: self.trackProductView.bind(self),
            trackSearchQuery: self.trackSearchQuery.bind(self),
            trackPageView: self.trackPageView.bind(self)
        };
        
        return self;
    };
});
