/**
 * DiscoverySuite RequireJS Mixin
 * 
 * Provides common functionality and integration points for Magento components
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

define([
    'jquery',
    'underscore',
    'mage/url',
    'mage/storage'
], function ($, _, urlBuilder, storage) {
    'use strict';

    /**
     * DiscoverySuite Mixin for Magento components
     */
    var discoveryMixin = {
        
        /**
         * Initialize Discovery SDK integration
         */
        initDiscoveryIntegration: function() {
            var self = this;
            
            // Wait for SDK to be available
            var checkSDK = function() {
                if (window.DiscoverySDK && window.DiscoverySDK.initialized) {
                    self.onDiscoverySDKReady();
                } else {
                    setTimeout(checkSDK, 100);
                }
            };
            checkSDK();
            
            return this;
        },
        
        /**
         * Called when Discovery SDK is ready
         */
        onDiscoverySDKReady: function() {
            // Override in component implementations
        },
        
        /**
         * Track Discovery event
         */
        trackDiscoveryEvent: function(eventType, eventData) {
            if (window.DiscoverySDK && window.DiscoverySDK.services.analytics) {
                window.DiscoverySDK.services.analytics.trackEvent(eventType, eventData);
            }
        },
        
        /**
         * Get A/B test variant
         */
        getABTestVariant: function(testName) {
            if (window.DiscoverySDK && window.DiscoverySDK.getABTestVariant) {
                return window.DiscoverySDK.getABTestVariant(testName);
            }
            return 'A'; // Default variant
        },
        
        /**
         * Get recommendations
         */
        getDiscoveryRecommendations: function(context, options) {
            if (window.DiscoverySDK && window.DiscoverySDK.services.recommendations) {
                return window.DiscoverySDK.services.recommendations.getRecommendations(context, options);
            }
            
            // Fallback to direct API call
            var data = $.extend({
                context: context,
                store_id: window.STORE_ID || 1
            }, options);
            
            return storage.post(
                urlBuilder.build('discoverysuite/recommendations/get'),
                JSON.stringify(data),
                false
            );
        },
        
        /**
         * Perform Discovery search
         */
        performDiscoverySearch: function(query, options) {
            if (window.DiscoverySDK && window.DiscoverySDK.services.search) {
                return window.DiscoverySDK.services.search.search(query, options);
            }
            
            // Fallback to direct API call
            var data = $.extend({
                q: query,
                store_id: window.STORE_ID || 1
            }, options);
            
            return storage.post(
                urlBuilder.build('discoverysuite/search/index'),
                JSON.stringify(data),
                false
            );
        },
        
        /**
         * Start assistant session
         */
        startAssistantSession: function(userContext) {
            if (window.DiscoverySDK && window.DiscoverySDK.services.assistant) {
                return window.DiscoverySDK.services.assistant.startSession(userContext);
            }
            
            // Fallback to direct API call
            var data = {
                user_context: userContext || {},
                store_id: window.STORE_ID || 1
            };
            
            return storage.post(
                urlBuilder.build('discoverysuite/assistant/session'),
                JSON.stringify(data),
                false
            );
        },
        
        /**
         * Enhanced error handling with Discovery analytics
         */
        handleDiscoveryError: function(error, context) {
            console.error('Discovery Error:', error);
            
            // Track error in analytics
            this.trackDiscoveryEvent('component_error', {
                error_message: error.message || error,
                error_context: context || 'unknown',
                component_name: this.component || 'unknown',
                stack_trace: error.stack || null
            });
        },
        
        /**
         * Performance monitoring wrapper
         */
        withPerformanceTracking: function(operationName, callback) {
            var startTime = performance.now();
            var self = this;
            
            var trackPerformance = function(success, error) {
                var endTime = performance.now();
                var duration = endTime - startTime;
                
                self.trackDiscoveryEvent('performance_metric', {
                    operation: operationName,
                    duration_ms: Math.round(duration),
                    success: success,
                    error: error || null,
                    component: self.component || 'unknown'
                });
            };
            
            try {
                var result = callback();
                
                // Handle promises
                if (result && typeof result.then === 'function') {
                    return result
                        .then(function(data) {
                            trackPerformance(true);
                            return data;
                        })
                        .catch(function(error) {
                            trackPerformance(false, error.message);
                            throw error;
                        });
                } else {
                    trackPerformance(true);
                    return result;
                }
            } catch (error) {
                trackPerformance(false, error.message);
                throw error;
            }
        },
        
        /**
         * Debounced function creator with Discovery tracking
         */
        createDiscoveryDebounce: function(func, wait, options) {
            options = options || {};
            var self = this;
            var timeout;
            var callCount = 0;
            
            return function() {
                var context = this;
                var args = arguments;
                callCount++;
                
                var later = function() {
                    timeout = null;
                    
                    // Track debounce performance
                    if (options.trackPerformance) {
                        self.trackDiscoveryEvent('debounce_executed', {
                            function_name: options.name || 'unknown',
                            total_calls: callCount,
                            delay_ms: wait
                        });
                    }
                    
                    func.apply(context, args);
                    callCount = 0;
                };
                
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        /**
         * Smart cache wrapper with Discovery integration
         */
        withDiscoveryCache: function(key, dataFetcher, options) {
            options = $.extend({
                ttl: 300000, // 5 minutes default
                trackHits: true
            }, options);
            
            var self = this;
            var cacheKey = 'discovery_cache_' + key;
            var cached = this.getCachedData(cacheKey);
            
            if (cached && !this.isCacheExpired(cached, options.ttl)) {
                if (options.trackHits) {
                    this.trackDiscoveryEvent('cache_hit', {
                        cache_key: key,
                        component: this.component || 'unknown'
                    });
                }
                return Promise.resolve(cached.data);
            }
            
            // Cache miss - fetch new data
            if (options.trackHits) {
                this.trackDiscoveryEvent('cache_miss', {
                    cache_key: key,
                    component: this.component || 'unknown'
                });
            }
            
            return Promise.resolve(dataFetcher())
                .then(function(data) {
                    self.setCachedData(cacheKey, data);
                    return data;
                })
                .catch(function(error) {
                    self.handleDiscoveryError(error, 'cache_fetch');
                    throw error;
                });
        },
        
        /**
         * Cache utilities
         */
        getCachedData: function(key) {
            try {
                var cached = localStorage.getItem(key);
                return cached ? JSON.parse(cached) : null;
            } catch (e) {
                return null;
            }
        },
        
        setCachedData: function(key, data) {
            try {
                var cacheObject = {
                    data: data,
                    timestamp: Date.now()
                };
                localStorage.setItem(key, JSON.stringify(cacheObject));
            } catch (e) {
                // Ignore storage errors
            }
        },
        
        isCacheExpired: function(cached, ttl) {
            return !cached || (Date.now() - cached.timestamp) > ttl;
        },
        
        /**
         * Feature flag checking
         */
        isDiscoveryFeatureEnabled: function(featureName) {
            if (window.DiscoverySDK && window.DiscoverySDK.config.features) {
                return window.DiscoverySDK.config.features[featureName];
            }
            return false;
        },
        
        /**
         * User segment checking
         */
        isUserInSegment: function(segmentName) {
            var userSegments = window.DiscoverySDK?.utils?.storage?.get('user_segments', []);
            return userSegments.includes(segmentName);
        },
        
        /**
         * Progressive enhancement wrapper
         */
        withProgressiveEnhancement: function(enhancementCallback, fallbackCallback) {
            if (this.isDiscoveryFeatureEnabled('progressive_enhancement')) {
                try {
                    return enhancementCallback();
                } catch (error) {
                    this.handleDiscoveryError(error, 'progressive_enhancement');
                    return fallbackCallback ? fallbackCallback() : null;
                }
            }
            return fallbackCallback ? fallbackCallback() : null;
        }
    };

    /**
     * Auto-enhance existing Magento components
     */
    var enhanceComponent = function(component) {
        return $.extend(true, component, discoveryMixin);
    };

    // Auto-enhance common Magento components when they're loaded
    var originalDefine = window.define;
    if (originalDefine && originalDefine.amd) {
        // Intercept common Magento component definitions
        var componentsToEnhance = [
            'Magento_Catalog/js/catalog-add-to-cart',
            'Magento_Checkout/js/view/cart',
            'Magento_CatalogSearch/js/form-mini',
            'Magento_Catalog/js/product/view/provider',
            'Magento_Wishlist/js/add-to-wishlist'
        ];
        
        componentsToEnhance.forEach(function(componentName) {
            require([componentName], function(component) {
                if (component && typeof component === 'object') {
                    enhanceComponent(component);
                }
            }, function() {
                // Component not found, ignore
            });
        });
    }

    return {
        mixin: discoveryMixin,
        enhance: enhanceComponent
    };
});