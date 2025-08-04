/**
 * DiscoverySuite Recommendations Widget
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
    'mage/template',
    'mage/url',
    'Magento_Catalog/js/catalog-add-to-cart'
], function ($, _, mageTemplate, urlBuilder, catalogAddToCart) {
    'use strict';

    $.widget('discovery.discoveryRecommendations', {
        options: {
            enabled: true,
            context: 'homepage',
            limit: 12,
            layout: 'grid',
            url: '',
            trackingUrl: '',
            productId: null,
            customerId: null,
            storeId: 1,
            autoLoad: true,
            showLoadMore: false,
            animationDuration: 300
        },

        _create: function () {
            if (!this.options.enabled) {
                return;
            }

            this.container = this.element.find('#recommendations-container');
            this.loadingElement = this.element.find('.recommendations-loading');
            this.errorElement = this.element.find('.recommendations-error');
            this.actionsElement = this.element.find('.recommendations-actions');
            
            this.itemTemplate = mageTemplate($('#recommendation-item-template').html());
            this.gridTemplate = mageTemplate($('#recommendation-grid-template').html());
            this.sliderTemplate = mageTemplate($('#recommendation-slider-template').html());
            
            this.recommendationId = null;
            this.currentProducts = [];
            this.currentPage = 1;

            this._bindEvents();

            if (this.options.autoLoad) {
                this.loadRecommendations();
            }
        },

        _bindEvents: function () {
            var self = this;

            // Product interaction events
            this.container.on('click', '.recommendation-product-link', function (e) {
                var $this = $(this);
                var productId = $this.closest('.recommendation-item').data('product-id');
                var position = $this.data('position');
                var action = $this.data('action') || 'click';

                self._trackInteraction(productId, action, position);
            });

            // Add to cart events
            this.container.on('click', '.recommendation-add-to-cart', function (e) {
                e.preventDefault();
                var $this = $(this);
                var productId = $this.data('product-id');
                var position = $this.data('position');

                self._addToCart(productId, position);
            });

            // Add to wishlist events
            this.container.on('click', '.recommendation-add-to-wishlist', function (e) {
                e.preventDefault();
                var $this = $(this);
                var productId = $this.data('product-id');
                var position = $this.data('position');

                self._addToWishlist(productId, position);
            });

            // Add to compare events
            this.container.on('click', '.recommendation-add-to-compare', function (e) {
                e.preventDefault();
                var $this = $(this);
                var productId = $this.data('product-id');
                var position = $this.data('position');

                self._addToCompare(productId, position);
            });

            // Load more button
            this.element.on('click', '.load-more-recommendations', function (e) {
                e.preventDefault();
                self.loadMoreRecommendations();
            });

            // Slider controls
            this.container.on('click', '.slider-prev', function (e) {
                e.preventDefault();
                self._slideLeft();
            });

            this.container.on('click', '.slider-next', function (e) {
                e.preventDefault();
                self._slideRight();
            });

            // Intersection Observer for view tracking
            if ('IntersectionObserver' in window) {
                this._setupViewTracking();
            }
        },

        loadRecommendations: function () {
            var self = this;

            this._showLoading();

            var requestData = {
                context: this.options.context,
                store_id: this.options.storeId,
                limit: this.options.limit,
                customer_id: this.options.customerId
            };

            // Add context-specific parameters
            if (this.options.productId) {
                requestData.product_id = this.options.productId;
            }

            $.ajax({
                url: this.options.url,
                type: 'POST',
                dataType: 'json',
                data: requestData,
                success: function (data) {
                    self._handleSuccess(data);
                },
                error: function (xhr, status, error) {
                    self._handleError(error);
                }
            });
        },

        loadMoreRecommendations: function () {
            this.currentPage++;
            this.options.limit = this.options.limit + 6; // Load 6 more items
            this.loadRecommendations();
        },

        _handleSuccess: function (data) {
            if (data.products && data.products.length > 0) {
                this.currentProducts = data.products;
                this.recommendationId = data.recommendation_id;
                this._renderProducts(data.products);
                this._hideLoading();
                
                if (this.options.showLoadMore && data.has_more) {
                    this._showLoadMore();
                }

                // Track recommendation display
                this._trackDisplay();
            } else {
                this._hideLoading();
                this.element.hide(); // Hide widget if no recommendations
            }
        },

        _handleError: function (error) {
            console.warn('Recommendations loading failed:', error);
            this._hideLoading();
            this._showError();
        },

        _renderProducts: function (products) {
            var templateData = {
                products: products,
                recommendationId: this.recommendationId,
                itemTemplate: this.itemTemplate
            };

            var html;
            if (this.options.layout === 'slider') {
                html = this.sliderTemplate(templateData);
            } else {
                html = this.gridTemplate(templateData);
            }

            this.container.html(html);

            // Initialize slider if needed
            if (this.options.layout === 'slider') {
                this._initializeSlider();
            }

            // Animate items in
            this._animateIn();
        },

        _initializeSlider: function () {
            var slider = this.container.find('.recommendations-slider');
            var track = slider.find('.slider-track');
            var items = track.find('.slider-item');
            var prevBtn = slider.find('.slider-prev');
            var nextBtn = slider.find('.slider-next');

            if (items.length <= 4) {
                // Hide controls if not enough items
                slider.find('.slider-controls').hide();
                return;
            }

            var currentPosition = 0;
            var itemWidth = items.outerWidth(true);
            var visibleItems = 4;
            var maxPosition = items.length - visibleItems;

            function updateButtons() {
                prevBtn.prop('disabled', currentPosition <= 0);
                nextBtn.prop('disabled', currentPosition >= maxPosition);
            }

            this._slideLeft = function () {
                if (currentPosition > 0) {
                    currentPosition--;
                    track.css('transform', 'translateX(-' + (currentPosition * itemWidth) + 'px)');
                    updateButtons();
                }
            };

            this._slideRight = function () {
                if (currentPosition < maxPosition) {
                    currentPosition++;
                    track.css('transform', 'translateX(-' + (currentPosition * itemWidth) + 'px)');
                    updateButtons();
                }
            };

            updateButtons();
        },

        _addToCart: function (productId, position) {
            var self = this;

            // Use Magento's add to cart functionality
            var form = $('<form>', {
                action: urlBuilder.build('checkout/cart/add'),
                method: 'post'
            });

            form.append($('<input>', {
                type: 'hidden',
                name: 'product',
                value: productId
            }));

            form.append($('<input>', {
                type: 'hidden',
                name: 'qty',
                value: 1
            }));

            // Add form key for security
            form.append($('<input>', {
                type: 'hidden',
                name: 'form_key',
                value: $.mage.cookies.get('form_key')
            }));

            $('body').append(form);

            // Submit form
            catalogAddToCart({
                form: form,
                success: function () {
                    self._trackInteraction(productId, 'add_to_cart', position);
                    form.remove();
                },
                error: function () {
                    form.remove();
                }
            });
        },

        _addToWishlist: function (productId, position) {
            var url = urlBuilder.build('wishlist/index/add', {
                product: productId
            });

            window.location.href = url;
            this._trackInteraction(productId, 'add_to_wishlist', position);
        },

        _addToCompare: function (productId, position) {
            var url = urlBuilder.build('catalog/product_compare/add', {
                product: productId
            });

            $.post(url).done(function () {
                // Show success message
                var message = $('<div>').addClass('message-success success message')
                    .html('<div>You added product to the comparison list.</div>');
                $('.page.messages').html(message);
            });

            this._trackInteraction(productId, 'add_to_compare', position);
        },

        _trackInteraction: function (productId, action, position) {
            if (!this.options.trackingUrl || !this.recommendationId) {
                return;
            }

            var trackingData = {
                recommendation_id: this.recommendationId,
                product_id: productId,
                action: action,
                position: position,
                context: this.options.context,
                customer_id: this.options.customerId,
                timestamp: new Date().toISOString()
            };

            $.ajax({
                url: this.options.trackingUrl,
                type: 'POST',
                dataType: 'json',
                data: trackingData,
                async: true
            });

            // Track with global analytics if available
            if (window.discoveryAnalytics) {
                window.discoveryAnalytics.track('recommendation_interaction', trackingData);
            }
        },

        _trackDisplay: function () {
            if (!this.recommendationId) {
                return;
            }

            this._trackInteraction(null, 'display', 0);
        },

        _setupViewTracking: function () {
            var self = this;

            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        var productId = $(entry.target).data('product-id');
                        var position = $(entry.target).find('[data-position]').data('position');
                        
                        if (productId) {
                            self._trackInteraction(productId, 'view', position);
                            observer.unobserve(entry.target); // Track only once
                        }
                    }
                });
            }, {
                threshold: 0.5
            });

            // Observe recommendation items when they're added
            this.container.on('DOMNodeInserted', '.recommendation-item', function () {
                observer.observe(this);
            });
        },

        _animateIn: function () {
            var items = this.container.find('.recommendation-item');
            
            items.each(function (index) {
                $(this).css({
                    opacity: 0,
                    transform: 'translateY(20px)'
                }).delay(index * 100).animate({
                    opacity: 1
                }, {
                    duration: this.options.animationDuration,
                    step: function (now) {
                        $(this).css('transform', 'translateY(' + (20 * (1 - now)) + 'px)');
                    }
                });
            }.bind(this));
        },

        _showLoading: function () {
            this.loadingElement.show();
            this.container.hide();
            this.errorElement.hide();
        },

        _hideLoading: function () {
            this.loadingElement.hide();
            this.container.show();
        },

        _showError: function () {
            this.errorElement.show();
            this.container.hide();
        },

        _showLoadMore: function () {
            this.actionsElement.show();
        },

        refresh: function () {
            this.currentPage = 1;
            this.loadRecommendations();
        },

        _destroy: function () {
            this.container.off();
            this.element.off();
        }
    });

    return $.discovery.discoveryRecommendations;
});