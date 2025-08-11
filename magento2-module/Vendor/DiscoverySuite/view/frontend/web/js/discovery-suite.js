/**
 * AI Discovery Suite Frontend JavaScript
 */
define([
    'jquery',
    'mage/url',
    'mage/storage',
    'mage/cookies'
], function ($, url, storage, cookies) {
    'use strict';

    return {
        config: {},
        
        /**
         * Initialize Discovery Suite
         */
        init: function (config) {
            this.config = $.extend({}, this.config, config);
            this.bindGlobalEvents();
            this.initializeComponents();
        },

        /**
         * Bind global events
         */
        bindGlobalEvents: function () {
            var self = this;

            // Track page views
            $(document).ready(function () {
                self.trackPageView();
            });

            // Track product interactions
            $(document).on('click', '.discovery-product-item', function () {
                var productId = $(this).data('product-id');
                if (productId) {
                    self.trackProductClick(productId);
                }
            });

            // Track add to cart from recommendations
            $(document).on('click', '.discovery-add-to-cart', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var productId = $(this).data('product-id');
                if (productId) {
                    self.trackRecommendationClick(productId);
                }
            });
        },

        /**
         * Initialize components
         */
        initializeComponents: function () {
            this.initAutocomplete();
            this.initAssistant();
            this.initRecommendations();
            this.showComponents();
        },

        /**
         * Show components after initialization
         */
        showComponents: function () {
            $('.discovery-assistant-widget').show();
            $('.discovery-recommendations-container').addClass('discovery-fade-in');
        },

        /**
         * Initialize autocomplete
         */
        initAutocomplete: function () {
            var self = this;
            var searchInput = $('#search');
            var resultsContainer = $('#discovery-autocomplete-results');
            var searchTimeout;

            if (!searchInput.length || !resultsContainer.length) return;

            searchInput.on('input', function () {
                var query = $(this).val().trim();
                
                clearTimeout(searchTimeout);
                
                if (query.length < 2) {
                    resultsContainer.hide();
                    return;
                }

                searchTimeout = setTimeout(function () {
                    self.fetchAutocompleteResults(query, resultsContainer);
                }, 300);
            });

            // Hide results when clicking outside
            $(document).on('click', function (e) {
                if (!$(e.target).closest('#search, #discovery-autocomplete-results').length) {
                    resultsContainer.hide();
                }
            });

            // Handle keyboard navigation
            searchInput.on('keydown', function (e) {
                self.handleAutocompleteKeyboard(e, resultsContainer);
            });
        },

        /**
         * Fetch autocomplete results
         */
        fetchAutocompleteResults: function (query, container) {
            var autocompleteUrl = url.build('discovery/search/autocomplete');
            
            $.ajax({
                url: autocompleteUrl,
                type: 'GET',
                data: { q: query, limit: 10 },
                success: function (response) {
                    if (response.success && response.suggestions) {
                        this.displayAutocompleteResults(response.suggestions, container);
                    }
                }.bind(this),
                error: function () {
                    container.hide();
                }
            });
        },

        /**
         * Display autocomplete results
         */
        displayAutocompleteResults: function (suggestions, container) {
            var html = '';
            
            suggestions.forEach(function (suggestion, index) {
                html += '<div class="discovery-autocomplete-item" data-index="' + index + '">';
                
                if (suggestion.image) {
                    html += '<img src="' + suggestion.image + '" class="discovery-autocomplete-image" alt="' + suggestion.title + '">';
                }
                
                html += '<div class="discovery-autocomplete-details">';
                html += '<div class="discovery-autocomplete-title">' + suggestion.title + '</div>';
                
                if (suggestion.price) {
                    html += '<div class="discovery-autocomplete-price">' + suggestion.price + '</div>';
                }
                
                html += '</div></div>';
            });
            
            container.html(html).show();
        },

        /**
         * Handle autocomplete keyboard navigation
         */
        handleAutocompleteKeyboard: function (e, container) {
            var items = container.find('.discovery-autocomplete-item');
            var active = container.find('.discovery-autocomplete-item.active');
            
            if (e.keyCode === 40) { // Down arrow
                e.preventDefault();
                if (active.length === 0) {
                    items.first().addClass('active');
                } else {
                    active.removeClass('active').next().addClass('active');
                }
            } else if (e.keyCode === 38) { // Up arrow
                e.preventDefault();
                if (active.length > 0) {
                    active.removeClass('active').prev().addClass('active');
                }
            } else if (e.keyCode === 13) { // Enter
                if (active.length > 0) {
                    e.preventDefault();
                    // Handle selection
                    container.hide();
                }
            } else if (e.keyCode === 27) { // Escape
                container.hide();
            }
        },

        /**
         * Initialize shopping assistant
         */
        initAssistant: function () {
            var self = this;
            var widget = $('#discovery-assistant-widget');
            var toggle = $('#discovery-assistant-toggle');
            var chat = $('#discovery-assistant-chat');
            var minimize = $('#discovery-assistant-minimize');
            var input = $('#discovery-assistant-input-field');
            var send = $('#discovery-assistant-send');

            if (!widget.length) return;

            // Toggle chat window
            toggle.on('click', function () {
                if (chat.is(':visible')) {
                    chat.hide();
                } else {
                    chat.show();
                    input.focus();
                }
            });

            // Minimize chat
            minimize.on('click', function () {
                chat.hide();
            });

            // Send message
            send.on('click', function () {
                self.sendAssistantMessage();
            });

            // Send on Enter
            input.on('keypress', function (e) {
                if (e.which === 13) {
                    self.sendAssistantMessage();
                }
            });
        },

        /**
         * Send message to assistant
         */
        sendAssistantMessage: function () {
            var input = $('#discovery-assistant-input-field');
            var messages = $('#discovery-assistant-messages');
            var typing = $('#discovery-assistant-typing');
            var message = input.val().trim();

            if (!message) return;

            // Add user message
            messages.append('<div class="discovery-assistant-message discovery-assistant-user">' + message + '</div>');
            input.val('');
            
            // Show typing indicator
            typing.show();
            
            // Scroll to bottom
            messages.scrollTop(messages[0].scrollHeight);

            // Send to API
            var chatUrl = url.build('discovery/assistant/chat');
            $.ajax({
                url: chatUrl,
                type: 'POST',
                data: {
                    message: message,
                    session_id: this.getSessionId()
                },
                success: function (response) {
                    typing.hide();
                    if (response.success && response.reply) {
                        messages.append('<div class="discovery-assistant-message discovery-assistant-bot">' + response.reply + '</div>');
                        messages.scrollTop(messages[0].scrollHeight);
                    }
                },
                error: function () {
                    typing.hide();
                    messages.append('<div class="discovery-assistant-message discovery-assistant-bot">Sorry, I\'m having trouble right now. Please try again.</div>');
                    messages.scrollTop(messages[0].scrollHeight);
                }
            });
        },

        /**
         * Initialize recommendations
         */
        initRecommendations: function () {
            // Load recommendations dynamically if needed
            $('.discovery-recommendations-container').each(function () {
                var container = $(this);
                // Trigger any lazy loading or dynamic content
            });
        },

        /**
         * Track page view
         */
        trackPageView: function () {
            this.trackEvent('page_view', {
                url: window.location.href,
                title: document.title,
                referrer: document.referrer
            });
        },

        /**
         * Track product click
         */
        trackProductClick: function (productId) {
            this.trackEvent('product_click', {
                product_id: productId,
                source: 'recommendations'
            });
        },

        /**
         * Track recommendation click
         */
        trackRecommendationClick: function (productId) {
            this.trackEvent('recommendation_click', {
                product_id: productId,
                source: 'ai_recommendations'
            });
        },

        /**
         * Track generic event
         */
        trackEvent: function (eventType, eventData) {
            if (!this.config.trackingEnabled) return;

            var trackingUrl = url.build('discovery/analytics/track');
            $.ajax({
                url: trackingUrl,
                type: 'POST',
                data: {
                    event_type: eventType,
                    event_data: eventData
                },
                success: function (response) {
                    // Silent success
                },
                error: function () {
                    // Silent failure
                }
            });
        },

        /**
         * Get or create session ID
         */
        getSessionId: function () {
            var sessionId = cookies.get('discovery_session_id');
            if (!sessionId) {
                sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                cookies.set('discovery_session_id', sessionId, { expires: 1 }); // 1 day
            }
            return sessionId;
        }
    };
});

// Auto-initialize when DOM is ready
require(['jquery', 'discoveryMain'], function ($, discovery) {
    $(document).ready(function () {
        discovery.init({
            trackingEnabled: true
        });
    });
});