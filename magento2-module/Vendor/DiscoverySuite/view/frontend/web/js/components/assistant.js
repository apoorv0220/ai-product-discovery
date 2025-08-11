/**
 * AI Shopping Assistant Widget
 */
define([
    'jquery',
    'mage/url',
    'mage/cookies'
], function ($, url, cookies) {
    'use strict';

    $.widget('discovery.discoveryAssistant', {
        options: {
            enabled: true,
            userId: '',
            sessionEndpoint: '',
            chatEndpoint: '',
            position: 'bottom-right',
            theme: 'light',
            initialContext: {},
            welcomeMessage: 'Hi! How can I help you find the perfect product today?',
            placeholderText: 'Ask me anything about products...',
            minimized: true
        },

        _create: function () {
            if (!this.options.enabled) {
                return;
            }

            this.sessionId = null;
            this.isOpen = false;
            
            this._initializeWidget();
            this._bindEvents();
            
            if (!this.options.minimized) {
                this._openChat();
            }
        },

        _initializeWidget: function () {
            this.toggleButton = this.element.find('#discovery-assistant-toggle');
            this.chatWindow = this.element.find('#discovery-assistant-chat');
            this.messagesContainer = this.element.find('#discovery-assistant-messages');
            this.inputField = this.element.find('#discovery-assistant-input-field');
            this.sendButton = this.element.find('#discovery-assistant-send');
            this.minimizeButton = this.element.find('#discovery-assistant-minimize');
            this.typingIndicator = this.element.find('#discovery-assistant-typing');

            // Set position
            this.element.addClass('discovery-position-' + this.options.position);
            
            // Set theme
            this.element.addClass('discovery-theme-' + this.options.theme);
        },

        _bindEvents: function () {
            var self = this;

            this.toggleButton.on('click', function () {
                self._toggleChat();
            });

            this.minimizeButton.on('click', function () {
                self._closeChat();
            });

            this.sendButton.on('click', function () {
                self._sendMessage();
            });

            this.inputField.on('keypress', function (e) {
                if (e.which === 13 && !e.shiftKey) {
                    e.preventDefault();
                    self._sendMessage();
                }
            });

            // Auto-resize input
            this.inputField.on('input', function () {
                self._adjustInputHeight();
            });
        },

        _toggleChat: function () {
            if (this.isOpen) {
                this._closeChat();
            } else {
                this._openChat();
            }
        },

        _openChat: function () {
            this.chatWindow.show();
            this.isOpen = true;
            this.inputField.focus();
            
            if (!this.sessionId) {
                this._startSession();
            }
        },

        _closeChat: function () {
            this.chatWindow.hide();
            this.isOpen = false;
        },

        _startSession: function () {
            var self = this;

            $.ajax({
                url: this.options.sessionEndpoint,
                type: 'POST',
                data: {
                    user_id: this.options.userId,
                    context: this.options.initialContext
                },
                success: function (response) {
                    if (response.success && response.session_id) {
                        self.sessionId = response.session_id;
                        self._addMessage('bot', self.options.welcomeMessage);
                    }
                },
                error: function () {
                    self._addMessage('bot', 'Hello! I\'m here to help you find products.');
                }
            });
        },

        _sendMessage: function () {
            var message = this.inputField.val().trim();
            
            if (!message || !this.sessionId) {
                return;
            }

            this._addMessage('user', message);
            this.inputField.val('');
            this._adjustInputHeight();
            this._showTyping();

            this._sendToAPI(message);
        },

        _sendToAPI: function (message) {
            var self = this;

            $.ajax({
                url: this.options.chatEndpoint,
                type: 'POST',
                data: {
                    session_id: this.sessionId,
                    message: message,
                    context: this._getCurrentContext()
                },
                success: function (response) {
                    self._hideTyping();
                    
                    if (response.success && response.reply) {
                        self._addMessage('bot', response.reply);
                        
                        // Handle product recommendations in response
                        if (response.products) {
                            self._displayProductRecommendations(response.products);
                        }
                    } else {
                        self._addMessage('bot', 'I\'m sorry, I didn\'t understand that. Could you try rephrasing?');
                    }
                },
                error: function () {
                    self._hideTyping();
                    self._addMessage('bot', 'I\'m having trouble right now. Please try again in a moment.');
                }
            });
        },

        _addMessage: function (type, content) {
            var messageClass = 'discovery-assistant-message discovery-assistant-' + type;
            var messageHtml = '<div class="' + messageClass + '">' + content + '</div>';
            
            this.messagesContainer.append(messageHtml);
            this._scrollToBottom();
        },

        _displayProductRecommendations: function (products) {
            if (!products || !products.length) {
                return;
            }

            var html = '<div class="discovery-assistant-products">';
            
            products.forEach(function (product) {
                html += '<div class="discovery-assistant-product" data-product-id="' + product.id + '">';
                html += '<img src="' + product.image + '" alt="' + product.name + '" class="discovery-assistant-product-image">';
                html += '<div class="discovery-assistant-product-details">';
                html += '<div class="discovery-assistant-product-name">' + product.name + '</div>';
                html += '<div class="discovery-assistant-product-price">' + product.price + '</div>';
                html += '</div>';
                html += '<button class="discovery-assistant-product-button">View</button>';
                html += '</div>';
            });
            
            html += '</div>';
            
            this.messagesContainer.append(html);
            this._scrollToBottom();
        },

        _getCurrentContext: function () {
            return {
                page_url: window.location.href,
                page_type: this._getPageType(),
                products_viewed: this._getViewedProducts()
            };
        },

        _getPageType: function () {
            var path = window.location.pathname;
            
            if (path.includes('/product/')) {
                return 'product';
            } else if (path.includes('/category/')) {
                return 'category';
            } else if (path.includes('/search/')) {
                return 'search';
            } else if (path.includes('/checkout/')) {
                return 'checkout';
            }
            
            return 'other';
        },

        _getViewedProducts: function () {
            // Get recently viewed products from cookies or local storage
            var viewed = cookies.get('recently_viewed_products');
            return viewed ? JSON.parse(viewed) : [];
        },

        _showTyping: function () {
            this.typingIndicator.show();
            this._scrollToBottom();
        },

        _hideTyping: function () {
            this.typingIndicator.hide();
        },

        _scrollToBottom: function () {
            this.messagesContainer.scrollTop(this.messagesContainer[0].scrollHeight);
        },

        _adjustInputHeight: function () {
            var input = this.inputField[0];
            input.style.height = 'auto';
            input.style.height = input.scrollHeight + 'px';
        },

        _destroy: function () {
            this.element.off('click keypress input');
        }
    });

    return $.discovery.discoveryAssistant;
});