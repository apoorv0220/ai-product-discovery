/**
 * DiscoverySuite Knockout.js Custom Bindings
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

define([
    'knockout',
    'jquery',
    'underscore'
], function (ko, $, _) {
    'use strict';

    /**
     * Discovery Search binding
     * Usage: <div data-bind="discoverySearch: { query: searchTerm, options: searchOptions }"></div>
     */
    ko.bindingHandlers.discoverySearch = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var options = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            // Initialize search widget
            require(['Vendor_DiscoverySuite/js/discovery-autocomplete'], function () {
                $element.discoveryAutocomplete(options);
            });
        },
        
        update: function (element, valueAccessor) {
            var options = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            // Update search query if it changed
            if (options.query && $element.data('discoveryAutocomplete')) {
                var widget = $element.data('discoveryAutocomplete');
                if (widget.searchInput) {
                    widget.searchInput.val(ko.unwrap(options.query));
                }
            }
        }
    };

    /**
     * Discovery Recommendations binding
     * Usage: <div data-bind="discoveryRecommendations: { context: 'homepage', limit: 12 }"></div>
     */
    ko.bindingHandlers.discoveryRecommendations = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var options = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            // Initialize recommendations widget
            require(['Vendor_DiscoverySuite/js/discovery-recommendations'], function () {
                $element.discoveryRecommendations(options);
            });
        },
        
        update: function (element, valueAccessor) {
            var options = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            // Refresh recommendations if context changed
            if ($element.data('discoveryRecommendations')) {
                var widget = $element.data('discoveryRecommendations');
                if (widget.refresh) {
                    widget.refresh();
                }
            }
        }
    };

    /**
     * Discovery Analytics tracking binding
     * Usage: <button data-bind="discoveryTrack: { event: 'button_click', data: { button_id: 'cta' } }">Click me</button>
     */
    ko.bindingHandlers.discoveryTrack = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var trackingInfo = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            $element.on('click', function (e) {
                if (window.DiscoverySDK && window.DiscoverySDK.services.analytics) {
                    var eventType = ko.unwrap(trackingInfo.event) || 'element_click';
                    var eventData = ko.unwrap(trackingInfo.data) || {};
                    
                    // Add element information
                    eventData.element_type = element.tagName.toLowerCase();
                    eventData.element_text = $element.text().trim();
                    eventData.element_class = element.className;
                    eventData.element_id = element.id;
                    
                    window.DiscoverySDK.services.analytics.trackEvent(eventType, eventData);
                }
            });
        }
    };

    /**
     * Discovery Product tracking binding
     * Usage: <div data-bind="discoveryProductTrack: { productId: product.id, action: 'view' }"></div>
     */
    ko.bindingHandlers.discoveryProductTrack = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var trackingInfo = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            // Track product view when element becomes visible
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        if (window.DiscoverySDK && window.DiscoverySDK.services.analytics) {
                            var productId = ko.unwrap(trackingInfo.productId);
                            var action = ko.unwrap(trackingInfo.action) || 'view';
                            
                            window.DiscoverySDK.services.analytics.trackEvent('product_interaction', {
                                product_id: productId,
                                action: action,
                                context: trackingInfo.context || {}
                            });
                        }
                        observer.unobserve(element);
                    }
                });
            }, {
                threshold: 0.5
            });
            
            observer.observe(element);
        }
    };

    /**
     * Discovery A/B Test binding
     * Usage: <div data-bind="discoveryABTest: { test: 'button_color', variants: { A: 'btn-blue', B: 'btn-red' } }"></div>
     */
    ko.bindingHandlers.discoveryABTest = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var testInfo = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            if (window.DiscoverySDK && window.DiscoverySDK.getABTestVariant) {
                var testName = ko.unwrap(testInfo.test);
                var variants = ko.unwrap(testInfo.variants);
                var variant = window.DiscoverySDK.getABTestVariant(testName);
                
                // Apply variant-specific class or attribute
                if (variants && variants[variant]) {
                    if (typeof variants[variant] === 'string') {
                        $element.addClass(variants[variant]);
                    } else if (typeof variants[variant] === 'object') {
                        // Apply multiple attributes/classes
                        Object.keys(variants[variant]).forEach(function (key) {
                            if (key === 'class') {
                                $element.addClass(variants[variant][key]);
                            } else {
                                $element.attr(key, variants[variant][key]);
                            }
                        });
                    }
                }
                
                // Store variant for tracking
                $element.data('ab-test-variant', variant);
                $element.data('ab-test-name', testName);
            }
        }
    };

    /**
     * Discovery Assistant binding
     * Usage: <div data-bind="discoveryAssistant: { position: 'bottom_right', autoTrigger: true }"></div>
     */
    ko.bindingHandlers.discoveryAssistant = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var options = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            // Initialize assistant widget
            require(['Vendor_DiscoverySuite/js/discovery-assistant'], function () {
                $element.discoveryAssistant(options);
            });
        }
    };

    /**
     * Discovery Dynamic Content binding
     * Loads content dynamically based on user segment or A/B test
     * Usage: <div data-bind="discoveryDynamicContent: { segment: 'premium_customers', contentUrl: '/content/premium' }"></div>
     */
    ko.bindingHandlers.discoveryDynamicContent = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var options = ko.unwrap(valueAccessor());
            var $element = $(element);
            
            if (window.DiscoverySDK && window.DiscoverySDK.services.analytics) {
                // Get user segment or A/B test variant
                var shouldShow = true;
                
                if (options.segment) {
                    // Check if user belongs to segment (this would require server-side support)
                    shouldShow = window.DiscoverySDK.utils.storage.get('user_segment') === options.segment;
                }
                
                if (options.abTest) {
                    var variant = window.DiscoverySDK.getABTestVariant(options.abTest);
                    shouldShow = variant === (options.variant || 'B');
                }
                
                if (shouldShow && options.contentUrl) {
                    // Load dynamic content
                    $.get(options.contentUrl)
                        .done(function (content) {
                            $element.html(content);
                        })
                        .fail(function () {
                            if (options.fallbackContent) {
                                $element.html(options.fallbackContent);
                            }
                        });
                } else if (!shouldShow) {
                    $element.hide();
                }
            }
        }
    };

    /**
     * Discovery Lazy Load binding
     * Lazy loads recommendations or content when element becomes visible
     * Usage: <div data-bind="discoveryLazyLoad: { type: 'recommendations', context: 'homepage' }"></div>
     */
    ko.bindingHandlers.discoveryLazyLoad = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var options = ko.unwrap(valueAccessor());
            var $element = $(element);
            var loaded = false;
            
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting && !loaded) {
                        loaded = true;
                        
                        switch (options.type) {
                            case 'recommendations':
                                require(['Vendor_DiscoverySuite/js/discovery-recommendations'], function () {
                                    $element.discoveryRecommendations(options);
                                });
                                break;
                                
                            case 'search':
                                require(['Vendor_DiscoverySuite/js/discovery-autocomplete'], function () {
                                    $element.discoveryAutocomplete(options);
                                });
                                break;
                                
                            case 'content':
                                if (options.contentUrl) {
                                    $.get(options.contentUrl).done(function (content) {
                                        $element.html(content);
                                    });
                                }
                                break;
                        }
                        
                        observer.unobserve(element);
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '50px'
            });
            
            observer.observe(element);
        }
    };

    /**
     * Discovery Countdown Timer binding
     * Displays countdown for limited-time offers (useful with A/B testing)
     * Usage: <div data-bind="discoveryCountdown: { endTime: offerEndTime, format: 'HH:mm:ss' }"></div>
     */
    ko.bindingHandlers.discoveryCountdown = {
        init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
            var options = ko.unwrap(valueAccessor());
            var $element = $(element);
            var endTime = new Date(ko.unwrap(options.endTime));
            var format = ko.unwrap(options.format) || 'HH:mm:ss';
            
            function updateCountdown() {
                var now = new Date();
                var timeDiff = endTime - now;
                
                if (timeDiff <= 0) {
                    $element.html(options.expiredText || 'Offer expired');
                    if (options.onExpired && typeof options.onExpired === 'function') {
                        options.onExpired();
                    }
                    return;
                }
                
                var hours = Math.floor(timeDiff / (1000 * 60 * 60));
                var minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);
                
                var display = format
                    .replace('HH', hours.toString().padStart(2, '0'))
                    .replace('mm', minutes.toString().padStart(2, '0'))
                    .replace('ss', seconds.toString().padStart(2, '0'));
                
                $element.html(display);
            }
            
            updateCountdown();
            var interval = setInterval(updateCountdown, 1000);
            
            // Store interval for cleanup
            ko.utils.domNodeDisposal.addDisposeCallback(element, function () {
                clearInterval(interval);
            });
        }
    };

    return {
        // Export for manual registration if needed
        register: function () {
            // Bindings are automatically registered when this module loads
            console.log('DiscoverySuite Knockout bindings registered');
        }
    };
});