/**
 * DiscoverySuite JavaScript SDK
 * 
 * Unified SDK for all DiscoverySuite widgets and functionality
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
    'knockout',
    'mage/url',
    'mage/storage',
    'mage/translate'
], function ($, _, ko, urlBuilder, storage, $t) {
    'use strict';

    /**
     * DiscoverySuite SDK main object
     */
    var DiscoverySDK = {
        version: '1.0.0',
        initialized: false,
        config: {},
        widgets: {},
        services: {},
        utils: {},
        events: {}
    };

    /**
     * Initialize the SDK
     */
    DiscoverySDK.init = function(config) {
        if (this.initialized) {
            return this;
        }

        this.config = $.extend(true, {
            // Default configuration
            debug: false,
            baseUrl: '',
            apiKey: '',
            storeId: 1,
            customerId: null,
            sessionId: null,
            locale: 'en_US',
            currency: 'USD',
            
            // Feature flags
            features: {
                search: true,
                recommendations: true,
                analytics: true,
                assistant: true,
                abTesting: true
            },
            
            // Widget defaults
            widgets: {
                search: {
                    selector: '[data-discovery-search]',
                    autoInit: true
                },
                recommendations: {
                    selector: '[data-discovery-recommendations]',
                    autoInit: true
                },
                assistant: {
                    selector: '[data-discovery-assistant]',
                    autoInit: true
                }
            }
        }, config);

        // Initialize services
        this._initServices();
        
        // Initialize event system
        this._initEvents();
        
        // Initialize analytics
        if (this.config.features.analytics) {
            this._initAnalytics();
        }
        
        // Initialize A/B testing
        if (this.config.features.abTesting) {
            this._initABTesting();
        }
        
        // Auto-initialize widgets
        this._autoInitWidgets();
        
        this.initialized = true;
        this.trigger('sdk:initialized', this.config);
        
        return this;
    };

    /**
     * Initialize services
     */
    DiscoverySDK._initServices = function() {
        this.services = {
            search: new SearchService(this),
            recommendations: new RecommendationService(this),
            analytics: new AnalyticsService(this),
            assistant: new AssistantService(this),
            listing: new ListingService(this)
        };
    };

    /**
     * Initialize event system
     */
    DiscoverySDK._initEvents = function() {
        this.events = {
            listeners: {},
            
            on: function(event, callback, context) {
                if (!this.listeners[event]) {
                    this.listeners[event] = [];
                }
                this.listeners[event].push({
                    callback: callback,
                    context: context || null
                });
            },
            
            off: function(event, callback) {
                if (!this.listeners[event]) return;
                
                this.listeners[event] = this.listeners[event].filter(function(listener) {
                    return listener.callback !== callback;
                });
            },
            
            trigger: function(event, data) {
                if (!this.listeners[event]) return;
                
                this.listeners[event].forEach(function(listener) {
                    if (listener.context) {
                        listener.callback.call(listener.context, data);
                    } else {
                        listener.callback(data);
                    }
                });
            }
        };
        
        // Bind event methods to SDK
        this.on = this.events.on.bind(this.events);
        this.off = this.events.off.bind(this.events);
        this.trigger = this.events.trigger.bind(this.events);
    };

    /**
     * Initialize analytics
     */
    DiscoverySDK._initAnalytics = function() {
        var self = this;
        
        // Track page view
        this.services.analytics.trackPageView({
            page_type: this.utils.getPageType(),
            page_url: window.location.href,
            page_title: document.title
        });
        
        // Global click tracking
        $(document).on('click', '[data-track-click]', function(e) {
            var $element = $(this);
            var trackingData = $element.data('track-click');
            
            if (typeof trackingData === 'string') {
                try {
                    trackingData = JSON.parse(trackingData);
                } catch (e) {
                    trackingData = { custom_data: trackingData };
                }
            }
            
            self.services.analytics.trackEvent('element_click', trackingData);
        });
    };

    /**
     * Initialize A/B testing
     */
    DiscoverySDK._initABTesting = function() {
        this.abTests = {};
        
        this.getABTestVariant = function(testName) {
            if (this.abTests[testName]) {
                return this.abTests[testName];
            }
            
            // Simple hash-based assignment
            var userIdentifier = this.config.customerId || this.config.sessionId || 'anonymous';
            var hash = this.utils.hashString(testName + userIdentifier);
            var variant = hash % 2 === 0 ? 'A' : 'B';
            
            this.abTests[testName] = variant;
            
            // Track assignment
            this.services.analytics.trackEvent('ab_test_assigned', {
                test_name: testName,
                variant: variant,
                user_identifier: userIdentifier
            });
            
            return variant;
        };
    };

    /**
     * Auto-initialize widgets
     */
    DiscoverySDK._autoInitWidgets = function() {
        var self = this;
        
        // Initialize search widgets
        if (this.config.features.search && this.config.widgets.search.autoInit) {
            $(this.config.widgets.search.selector).each(function() {
                self.initSearchWidget(this);
            });
        }
        
        // Initialize recommendation widgets
        if (this.config.features.recommendations && this.config.widgets.recommendations.autoInit) {
            $(this.config.widgets.recommendations.selector).each(function() {
                self.initRecommendationWidget(this);
            });
        }
        
        // Initialize assistant widgets
        if (this.config.features.assistant && this.config.widgets.assistant.autoInit) {
            $(this.config.widgets.assistant.selector).each(function() {
                self.initAssistantWidget(this);
            });
        }
    };

    /**
     * Initialize search widget
     */
    DiscoverySDK.initSearchWidget = function(element, options) {
        var $element = $(element);
        var config = $.extend({}, $element.data(), options);
        
        require(['Vendor_DiscoverySuite/js/discovery-autocomplete'], function(AutocompleteWidget) {
            $element.discoveryAutocomplete(config);
        });
        
        return this;
    };

    /**
     * Initialize recommendation widget
     */
    DiscoverySDK.initRecommendationWidget = function(element, options) {
        var $element = $(element);
        var config = $.extend({}, $element.data(), options);
        
        require(['Vendor_DiscoverySuite/js/discovery-recommendations'], function(RecommendationWidget) {
            $element.discoveryRecommendations(config);
        });
        
        return this;
    };

    /**
     * Initialize assistant widget
     */
    DiscoverySDK.initAssistantWidget = function(element, options) {
        var $element = $(element);
        var config = $.extend({}, $element.data(), options);
        
        require(['Vendor_DiscoverySuite/js/discovery-assistant'], function(AssistantWidget) {
            $element.discoveryAssistant(config);
        });
        
        return this;
    };

    /**
     * Utility functions
     */
    DiscoverySDK.utils = {
        
        /**
         * Get current page type
         */
        getPageType: function() {
            var path = window.location.pathname;
            var body = document.body;
            
            if (body.classList.contains('cms-index-index')) return 'homepage';
            if (body.classList.contains('catalog-product-view')) return 'product';
            if (body.classList.contains('catalog-category-view')) return 'category';
            if (body.classList.contains('catalogsearch-result-index')) return 'search';
            if (body.classList.contains('checkout-cart-index')) return 'cart';
            if (body.classList.contains('checkout-index-index')) return 'checkout';
            if (body.classList.contains('checkout-onepage-success')) return 'success';
            
            return 'other';
        },
        
        /**
         * Generate hash from string
         */
        hashString: function(str) {
            var hash = 0;
            if (str.length === 0) return hash;
            
            for (var i = 0; i < str.length; i++) {
                var char = str.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }
            
            return Math.abs(hash);
        },
        
        /**
         * Debounce function
         */
        debounce: function(func, wait, immediate) {
            var timeout;
            return function() {
                var context = this, args = arguments;
                var later = function() {
                    timeout = null;
                    if (!immediate) func.apply(context, args);
                };
                var callNow = immediate && !timeout;
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
                if (callNow) func.apply(context, args);
            };
        },
        
        /**
         * Throttle function
         */
        throttle: function(func, limit) {
            var inThrottle;
            return function() {
                var args = arguments;
                var context = this;
                if (!inThrottle) {
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(function() {
                        inThrottle = false;
                    }, limit);
                }
            };
        },
        
        /**
         * Cookie utilities
         */
        cookie: {
            get: function(name) {
                var value = "; " + document.cookie;
                var parts = value.split("; " + name + "=");
                if (parts.length === 2) {
                    return parts.pop().split(";").shift();
                }
                return null;
            },
            
            set: function(name, value, days) {
                var expires = "";
                if (days) {
                    var date = new Date();
                    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
                    expires = "; expires=" + date.toUTCString();
                }
                document.cookie = name + "=" + value + expires + "; path=/";
            },
            
            remove: function(name) {
                document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/";
            }
        },
        
        /**
         * Local storage utilities
         */
        storage: {
            isSupported: function() {
                try {
                    var test = 'test';
                    localStorage.setItem(test, test);
                    localStorage.removeItem(test);
                    return true;
                } catch (e) {
                    return false;
                }
            },
            
            get: function(key, defaultValue) {
                if (!this.isSupported()) return defaultValue;
                
                try {
                    var value = localStorage.getItem('discovery_' + key);
                    return value ? JSON.parse(value) : defaultValue;
                } catch (e) {
                    return defaultValue;
                }
            },
            
            set: function(key, value) {
                if (!this.isSupported()) return false;
                
                try {
                    localStorage.setItem('discovery_' + key, JSON.stringify(value));
                    return true;
                } catch (e) {
                    return false;
                }
            },
            
            remove: function(key) {
                if (!this.isSupported()) return false;
                
                try {
                    localStorage.removeItem('discovery_' + key);
                    return true;
                } catch (e) {
                    return false;
                }
            }
        }
    };

    /**
     * Search Service
     */
    function SearchService(sdk) {
        this.sdk = sdk;
    }
    
    SearchService.prototype.search = function(query, options) {
        var data = $.extend({
            q: query,
            store_id: this.sdk.config.storeId
        }, options);
        
        return storage.post(
            urlBuilder.build('discoverysuite/search/index'),
            JSON.stringify(data),
            false
        );
    };
    
    SearchService.prototype.autocomplete = function(query, options) {
        var data = $.extend({
            q: query,
            store_id: this.sdk.config.storeId
        }, options);
        
        return storage.post(
            urlBuilder.build('discoverysuite/search/autocomplete'),
            JSON.stringify(data),
            false
        );
    };

    /**
     * Recommendation Service
     */
    function RecommendationService(sdk) {
        this.sdk = sdk;
    }
    
    RecommendationService.prototype.getRecommendations = function(context, options) {
        var data = $.extend({
            context: context,
            store_id: this.sdk.config.storeId,
            customer_id: this.sdk.config.customerId
        }, options);
        
        return storage.post(
            urlBuilder.build('discoverysuite/recommendations/get'),
            JSON.stringify(data),
            false
        );
    };
    
    RecommendationService.prototype.trackInteraction = function(recommendationId, productId, action, metadata) {
        var data = {
            recommendation_id: recommendationId,
            product_id: productId,
            action: action,
            metadata: metadata || {},
            customer_id: this.sdk.config.customerId,
            session_id: this.sdk.config.sessionId
        };
        
        return storage.post(
            urlBuilder.build('discoverysuite/recommendations/track'),
            JSON.stringify(data),
            false
        );
    };

    /**
     * Analytics Service
     */
    function AnalyticsService(sdk) {
        this.sdk = sdk;
        this.eventQueue = [];
        this.flushInterval = 5000; // 5 seconds
        this._startFlushTimer();
    }
    
    AnalyticsService.prototype.trackEvent = function(eventType, eventData, immediate) {
        var event = {
            event_type: eventType,
            event_data: eventData || {},
            customer_id: this.sdk.config.customerId,
            session_id: this.sdk.config.sessionId,
            store_id: this.sdk.config.storeId,
            timestamp: new Date().toISOString(),
            page_url: window.location.href,
            referrer: document.referrer
        };
        
        if (immediate) {
            this._sendEvent(event);
        } else {
            this.eventQueue.push(event);
        }
        
        // Trigger local event
        this.sdk.trigger('analytics:event', event);
    };
    
    AnalyticsService.prototype.trackPageView = function(pageData) {
        this.trackEvent('page_view', pageData, true);
    };
    
    AnalyticsService.prototype._sendEvent = function(event) {
        return storage.post(
            urlBuilder.build('discoverysuite/analytics/track'),
            JSON.stringify(event),
            false
        );
    };
    
    AnalyticsService.prototype._flushEvents = function() {
        if (this.eventQueue.length === 0) return;
        
        var events = this.eventQueue.splice(0);
        var self = this;
        
        events.forEach(function(event) {
            self._sendEvent(event);
        });
    };
    
    AnalyticsService.prototype._startFlushTimer = function() {
        var self = this;
        setInterval(function() {
            self._flushEvents();
        }, this.flushInterval);
    };

    /**
     * Assistant Service
     */
    function AssistantService(sdk) {
        this.sdk = sdk;
        this.currentSession = null;
    }
    
    AssistantService.prototype.startSession = function(userContext) {
        var data = {
            user_context: userContext || {},
            customer_id: this.sdk.config.customerId,
            store_id: this.sdk.config.storeId
        };
        
        var self = this;
        return storage.post(
            urlBuilder.build('discoverysuite/assistant/session'),
            JSON.stringify(data),
            false
        ).done(function(response) {
            self.currentSession = response.session_id;
        });
    };
    
    AssistantService.prototype.sendMessage = function(message, context) {
        if (!this.currentSession) {
            throw new Error('No active session. Call startSession() first.');
        }
        
        var data = {
            session_id: this.currentSession,
            message: message,
            context: context || {}
        };
        
        return storage.post(
            urlBuilder.build('discoverysuite/assistant/chat'),
            JSON.stringify(data),
            false
        );
    };

    /**
     * Listing Service
     */
    function ListingService(sdk) {
        this.sdk = sdk;
    }
    
    ListingService.prototype.getDynamicFilters = function(categoryId) {
        var data = {
            category_id: categoryId,
            store_id: this.sdk.config.storeId
        };
        
        return storage.post(
            urlBuilder.build('discoverysuite/listing/filters'),
            JSON.stringify(data),
            false
        );
    };

    // Global error handling
    window.addEventListener('error', function(e) {
        if (DiscoverySDK.initialized && DiscoverySDK.config.features.analytics) {
            DiscoverySDK.services.analytics.trackEvent('javascript_error', {
                message: e.message,
                filename: e.filename,
                line: e.lineno,
                column: e.colno,
                stack: e.error ? e.error.stack : null
            });
        }
    });

    // Expose SDK globally
    window.DiscoverySDK = DiscoverySDK;
    
    return DiscoverySDK;
});