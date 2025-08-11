/**
 * AI Recommendations Widget
 */
define([
    'jquery',
    'mage/url',
    'mage/storage'
], function ($, url, storage) {
    'use strict';

    $.widget('discovery.discoveryRecommendations', {
        options: {
            enabled: true,
            userId: '',
            context: 'homepage',
            trackingEndpoint: '',
            limit: 12
        },

        _create: function () {
            if (!this.options.enabled) {
                return;
            }

            this._bindEvents();
            this._initTracking();
        },

        _bindEvents: function () {
            var self = this;

            // Track product clicks
            this.element.on('click', '.discovery-product-item', function () {
                var productId = $(this).data('product-id');
                if (productId) {
                    self._trackEvent('product_click', {
                        product_id: productId,
                        source: 'recommendations',
                        context: self.options.context
                    });
                }
            });

            // Track add to cart clicks
            this.element.on('click', '.discovery-add-to-cart', function (e) {
                e.preventDefault();
                e.stopPropagation();
                
                var productId = $(this).data('product-id');
                if (productId) {
                    self._trackEvent('recommendation_add_to_cart', {
                        product_id: productId,
                        source: 'ai_recommendations',
                        context: self.options.context
                    });
                    
                    // Trigger actual add to cart functionality
                    self._addToCart(productId, $(this));
                }
            });
        },

        _initTracking: function () {
            // Track recommendation view
            this._trackEvent('recommendations_view', {
                context: this.options.context,
                product_count: this.element.find('.discovery-product-item').length
            });
        },

        _addToCart: function (productId, button) {
            var self = this;
            var originalText = button.text();
            
            button.text('Adding...').prop('disabled', true);

            // This would integrate with Magento's add to cart functionality
            // For now, we'll just simulate it
            setTimeout(function () {
                button.text('Added!').removeClass('discovery-add-to-cart').addClass('discovery-added');
                
                setTimeout(function () {
                    button.text(originalText).prop('disabled', false);
                    button.removeClass('discovery-added').addClass('discovery-add-to-cart');
                }, 2000);
            }, 1000);
        },

        _trackEvent: function (eventType, eventData) {
            if (!this.options.trackingEndpoint) {
                return;
            }

            $.ajax({
                url: this.options.trackingEndpoint,
                type: 'POST',
                data: {
                    event_type: eventType,
                    event_data: eventData,
                    user_id: this.options.userId
                },
                success: function () {
                    // Silent success
                },
                error: function () {
                    // Silent failure
                }
            });
        },

        _destroy: function () {
            this.element.off('click');
        }
    });

    return $.discovery.discoveryRecommendations;
});