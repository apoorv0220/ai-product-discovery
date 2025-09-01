/**
 * Product Interaction Tracking for Personalized Search
 * Tracks user behavior to boost products in search results
 */

define([
    'jquery',
    'Vendor_DiscoverySuite/js/utils/session'
], function ($, sessionUtils) {
    'use strict';

    $.widget('discovery.productTracking', {
        options: {
            trackingApiUrl: 'http://localhost:7001/api/v1/tracking/product-view',
            enabled: true
        },

        _create: function () {
            if (this.options.enabled) {
                this._initTracking();
            }
        },

        _initTracking: function () {
            var self = this;
            
            // Initialize tracking based on page type
            if (this._isProductPage()) {
                this._initProductPageTracking();
            }
            
            // Track page views for all pages
            this._trackPageView();
        },

        _isProductPage: function() {
            return window.location.pathname.includes('/product/') || 
                   window.location.pathname.match(/\.html$/) ||
                   $('body').hasClass('catalog-product-view');
        },

        _initProductPageTracking: function() {
            var self = this;
            var productData = this._extractProductData();
            
            if (productData.id) {
                // Track initial page load
                this._trackProductView(productData);
                
                // Track if user stays on page for more than 10 seconds
                setTimeout(function() {
                    self._trackProductView(productData);
                }, 10000);
                
                console.log('🎯 Product tracking initialized for:', productData.name);
            }
        },

        _extractProductData: function() {
            var productData = {};
            
            // Try to get from global productData
            if (window.productData && window.productData.id) {
                return window.productData;
            }
            
            // Extract from DOM
            var productId = $('input[name="product"]').val() ||
                           $('[data-product-id]').first().data('product-id') ||
                           $('body').data('product-id');
            
            if (productId) {
                productData.id = productId;
                
                // Get product name
                productData.name = $('.page-title .base').text().trim() ||
                                 $('h1.product-name').text().trim() ||
                                 document.title.split(' - ')[0];
                
                // Get SKU
                productData.sku = $('.product-info-main [data-th="SKU"]').text().trim() ||
                                $('[data-product-sku]').first().data('product-sku');
                
                // Get categories from breadcrumbs
                var categories = [];
                $('.breadcrumbs .item').each(function() {
                    var categoryName = $(this).find('a').text().trim();
                    if (categoryName && categoryName !== 'Home') {
                        categories.push(categoryName);
                    }
                });
                productData.categories = categories;
            }
            
            return productData;
        },

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
                url: this.options.trackingApiUrl,
                type: 'POST',
                data: JSON.stringify(trackingData),
                contentType: 'application/json',
                success: function(response) {
                    console.log('✅ Product view tracked successfully:', productData.name);
                },
                error: function(xhr, status, error) {
                    console.warn('❌ Failed to track product view:', error);
                }
            });
        },

        _isFromSearch: function() {
            var referrer = document.referrer || '';
            var searchParams = new URLSearchParams(window.location.search);
            return referrer.includes('/catalogsearch/result/') || 
                   searchParams.has('q') || 
                   sessionStorage.getItem('came_from_search') === 'true';
        },

        _getSearchQuery: function() {
            var searchParams = new URLSearchParams(window.location.search);
            var query = searchParams.get('q') || sessionStorage.getItem('last_search_query');
            
            // Clear the flag after getting it
            sessionStorage.removeItem('came_from_search');
            
            return query;
        },

        _trackPageView: function() {
            // Basic page view tracking
            console.log('📄 Page view tracked for:', window.location.pathname);
        }
    });

    // Auto-initialize on document ready
    $(document).ready(function() {
        $('body').productTracking();
    });

    return $.discovery.productTracking;
});
