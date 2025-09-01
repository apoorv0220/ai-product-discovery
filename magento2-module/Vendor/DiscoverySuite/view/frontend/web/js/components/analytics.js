/**
 * AI Analytics Tracking Widget
 */
define([
    'jquery',
    'mage/url',
    'Vendor_DiscoverySuite/js/utils/session'
], function ($, url, sessionUtils) {
    'use strict';

    $.widget('discovery.discoveryAnalytics', {
        options: {
            enabled: true,
            userId: '',
            trackingEndpoint: '',
            pageData: {},
            sessionData: {},
            autoTrack: {
                pageView: true,
                productView: true,
                categoryView: true,
                searchQuery: true,
                addToCart: true,
                removeFromCart: true,
                checkout: true,
                purchase: true
            }
        },

        _create: function () {
            if (!this.options.enabled) {
                return;
            }

            this.sessionId = this._getOrCreateSessionId();
            this._initializeTracking();
            this._bindEvents();
        },

        _initializeTracking: function () {
            if (this.options.autoTrack.pageView) {
                this._trackPageView();
            }

            // Track based on page type
            var pageType = this.options.pageData.type;
            
            if (pageType === 'product' && this.options.autoTrack.productView) {
                this._trackProductView();
            } else if (pageType === 'category' && this.options.autoTrack.categoryView) {
                this._trackCategoryView();
            } else if (pageType === 'search' && this.options.autoTrack.searchQuery) {
                this._trackSearchQuery();
            } else if (pageType === 'purchase_success' && this.options.autoTrack.purchase) {
                this._trackPurchase();
            }
        },

        _bindEvents: function () {
            var self = this;

            // Track add to cart events
            if (this.options.autoTrack.addToCart) {
                $(document).on('click', '[data-role="tocart-form"] button[type="submit"], .action.tocart', function () {
                    self._trackAddToCart($(this));
                });
            }

            // Track search submissions
            if (this.options.autoTrack.searchQuery) {
                $('#search_mini_form, .block-search').on('submit', function () {
                    var query = $(this).find('input[name="q"]').val();
                    if (query) {
                        self._trackSearch(query);
                    }
                });
            }

            // Track product interactions
            $(document).on('click', '.product-item-link, .product-item-photo', function () {
                var productId = self._extractProductId($(this));
                if (productId) {
                    self._trackProductInteraction(productId, 'click');
                }
            });

            // Track wishlist additions
            $(document).on('click', '.action.towishlist', function () {
                var productId = self._extractProductId($(this));
                if (productId) {
                    self._trackWishlistAdd(productId);
                }
            });

            // Track scroll depth
            this._trackScrollDepth();
        },

        _trackPageView: function () {
            this._sendEvent('page_view', {
                url: this.options.pageData.url,
                title: this.options.pageData.title,
                referrer: this.options.pageData.referrer,
                page_type: this.options.pageData.type,
                timestamp: Date.now()
            });
        },

        _trackProductView: function () {
            if (this.options.pageData.product) {
                this._sendEvent('product_view', {
                    product_id: this.options.pageData.product.id,
                    product_sku: this.options.pageData.product.sku,
                    product_name: this.options.pageData.product.name,
                    product_price: this.options.pageData.product.price,
                    category_ids: this.options.pageData.product.category_ids,
                    timestamp: Date.now()
                });
            }
        },

        _trackCategoryView: function () {
            if (this.options.pageData.category) {
                this._sendEvent('category_view', {
                    category_id: this.options.pageData.category.id,
                    category_name: this.options.pageData.category.name,
                    category_path: this.options.pageData.category.path,
                    timestamp: Date.now()
                });
            }
        },

        _trackSearchQuery: function () {
            var query = this._getSearchQuery();
            if (query) {
                this._trackSearch(query);
            }
        },

        _trackPurchase: function () {
            if (this.options.sessionData.last_order) {
                this._sendEvent('purchase', {
                    order_id: this.options.sessionData.last_order.id,
                    order_total: this.options.sessionData.last_order.total,
                    items: this.options.sessionData.last_order.items,
                    timestamp: Date.now()
                });
            }
        },

        _trackAddToCart: function (button) {
            var form = button.closest('form');
            var productId = form.find('input[name="product"]').val();
            var qty = form.find('input[name="qty"]').val() || 1;

            if (productId) {
                this._sendEvent('add_to_cart', {
                    product_id: productId,
                    quantity: parseInt(qty),
                    source: 'product_page',
                    timestamp: Date.now()
                });
            }
        },

        _trackSearch: function (query) {
            this._sendEvent('search_query', {
                query: query,
                results_count: this._getSearchResultsCount(),
                timestamp: Date.now()
            });
        },

        _trackProductInteraction: function (productId, action) {
            this._sendEvent('product_interaction', {
                product_id: productId,
                action: action,
                source: 'listing',
                timestamp: Date.now()
            });
        },

        _trackWishlistAdd: function (productId) {
            this._sendEvent('wishlist_add', {
                product_id: productId,
                timestamp: Date.now()
            });
        },

        _trackScrollDepth: function () {
            var self = this;
            var maxScroll = 0;
            var tracked = [];

            $(window).on('scroll', function () {
                var scrollTop = $(window).scrollTop();
                var docHeight = $(document).height();
                var winHeight = $(window).height();
                var scrollPercent = Math.round((scrollTop / (docHeight - winHeight)) * 100);

                if (scrollPercent > maxScroll) {
                    maxScroll = scrollPercent;

                    // Track at 25%, 50%, 75%, and 100%
                    var milestones = [25, 50, 75, 100];
                    milestones.forEach(function (milestone) {
                        if (scrollPercent >= milestone && tracked.indexOf(milestone) === -1) {
                            tracked.push(milestone);
                            self._sendEvent('scroll_depth', {
                                depth_percent: milestone,
                                url: window.location.href,
                                timestamp: Date.now()
                            });
                        }
                    });
                }
            });
        },

        _sendEvent: function (eventType, eventData) {
            if (!this.options.trackingEndpoint) {
                return;
            }

            // Add common data
            eventData.session_id = this.sessionId;
            eventData.user_id = this.options.userId;
            eventData.user_agent = navigator.userAgent;
            eventData.screen_resolution = screen.width + 'x' + screen.height;
            eventData.viewport_size = $(window).width() + 'x' + $(window).height();

            $.ajax({
                url: this.options.trackingEndpoint,
                type: 'POST',
                data: {
                    event_type: eventType,
                    event_data: eventData
                },
                success: function () {
                    // Silent success
                },
                error: function () {
                    // Silent failure - don't interfere with user experience
                }
            });
        },

        _getOrCreateSessionId: function () {
            return sessionUtils.getAnalyticsSessionId();
        },

        _extractProductId: function (element) {
            var href = element.attr('href') || element.closest('a').attr('href');
            if (href) {
                var matches = href.match(/\/product\/(\d+)/);
                return matches ? matches[1] : null;
            }
            return null;
        },

        _getSearchQuery: function () {
            var urlParams = new URLSearchParams(window.location.search);
            return urlParams.get('q') || '';
        },

        _getSearchResultsCount: function () {
            var resultsText = $('.search-results').text();
            var matches = resultsText.match(/(\d+)\s+items?/);
            return matches ? parseInt(matches[1]) : 0;
        },

        _destroy: function () {
            $(document).off('click');
            $(window).off('scroll');
        }
    });

    return $.discovery.discoveryAnalytics;
});