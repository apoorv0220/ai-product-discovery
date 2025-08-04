/**
 * DiscoverySuite Shopping Assistant Widget
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
    'mage/template'
], function ($, _, mageTemplate) {
    'use strict';

    $.widget('discovery.discoveryAssistant', {
        options: {
            enabled: true,
            position: 'bottom_right',
            chatEnabled: true,
            guidedFlowEnabled: true,
            autoTriggerDelay: 30,
            customerId: null,
            storeId: 1,
            sessionUrl: '',
            chatUrl: '',
            flowUrl: '',
            trackingUrl: '',
            availableFlows: []
        },

        _create: function () {
            if (!this.options.enabled) {
                return;
            }

            this.trigger = this.element.find('#assistant-trigger');
            this.window = this.element.find('#assistant-window');
            this.chatMessages = this.element.find('#chat-messages');
            this.chatInput = this.element.find('#chat-input');
            this.sendBtn = this.element.find('#send-btn');
            this.quickActions = this.element.find('#quick-actions');
            this.guidedFlow = this.element.find('#guided-flow');
            this.productSuggestions = this.element.find('#product-suggestions');
            this.typingIndicator = this.element.find('#assistant-typing');

            // Templates
            this.userMessageTemplate = mageTemplate($('#user-message-template').html());
            this.assistantMessageTemplate = mageTemplate($('#assistant-message-template').html());
            this.productSuggestionTemplate = mageTemplate($('#product-suggestion-template').html());
            this.guidedFlowQuestionTemplate = mageTemplate($('#guided-flow-question-template').html());

            // State
            this.sessionId = null;
            this.isOpen = false;
            this.currentFlow = null;
            this.flowStep = 0;
            this.flowAnswers = {};
            this.messageHistory = [];

            this._bindEvents();
            this._setupAutoTrigger();
        },

        _bindEvents: function () {
            var self = this;

            // Trigger button events
            this.trigger.on('click', function () {
                self.toggleWindow();
            });

            // Window controls
            this.element.on('click', '.close-btn', function () {
                self.closeWindow();
            });

            this.element.on('click', '.minimize-btn', function () {
                self.minimizeWindow();
            });

            // Chat input events
            this.chatInput.on('keypress', function (e) {
                if (e.which === 13) { // Enter key
                    e.preventDefault();
                    self.sendMessage();
                }
            });

            this.sendBtn.on('click', function () {
                self.sendMessage();
            });

            // Quick action buttons
            this.quickActions.on('click', '.action-btn', function (e) {
                var action = $(this).data('action');
                self.handleQuickAction(action);
            });

            // Quick reply buttons
            this.chatMessages.on('click', '.quick-reply-btn', function (e) {
                var reply = $(this).data('reply');
                self.sendMessage(reply);
            });

            // Product suggestion actions
            this.productSuggestions.on('click', '.btn-view-product', function (e) {
                var url = $(this).data('url');
                if (url) {
                    window.open(url, '_blank');
                    self.trackInteraction('product_view', { url: url });
                }
            });

            // Guided flow actions
            this.guidedFlow.on('click', '.btn-next', function (e) {
                self.processFlowStep();
            });

            this.guidedFlow.on('click', '.btn-skip', function (e) {
                self.skipFlowStep();
            });

            // Auto-hide on outside click
            $(document).on('click', function (e) {
                if (!self.element.is(e.target) && self.element.has(e.target).length === 0) {
                    if (self.isOpen && !self.element.hasClass('sticky')) {
                        // Optional: auto-minimize on outside click
                    }
                }
            });
        },

        _setupAutoTrigger: function () {
            var self = this;
            
            if (this.options.autoTriggerDelay > 0) {
                setTimeout(function () {
                    if (!self.isOpen) {
                        self.showNotification();
                    }
                }, this.options.autoTriggerDelay * 1000);
            }
        },

        toggleWindow: function () {
            if (this.isOpen) {
                this.closeWindow();
            } else {
                this.openWindow();
            }
        },

        openWindow: function () {
            var self = this;

            this.window.show();
            this.trigger.addClass('active');
            this.isOpen = true;
            this.hideNotification();

            // Start session if not already started
            if (!this.sessionId) {
                this.startSession();
            }

            // Animate window opening
            this.window.css({
                transform: 'scale(0.8)',
                opacity: 0
            }).animate({
                opacity: 1
            }, {
                duration: 300,
                step: function (now) {
                    $(this).css('transform', 'scale(' + (0.8 + (0.2 * now)) + ')');
                },
                complete: function () {
                    self.chatInput.focus();
                }
            });

            this.trackInteraction('window_opened');
        },

        closeWindow: function () {
            var self = this;

            this.window.animate({
                opacity: 0
            }, {
                duration: 200,
                step: function (now) {
                    $(this).css('transform', 'scale(' + (0.8 + (0.2 * now)) + ')');
                },
                complete: function () {
                    self.window.hide();
                    self.trigger.removeClass('active');
                    self.isOpen = false;
                }
            });

            this.trackInteraction('window_closed');
        },

        minimizeWindow: function () {
            this.closeWindow();
            this.showNotification();
        },

        showNotification: function () {
            this.trigger.find('.trigger-notification').show();
        },

        hideNotification: function () {
            this.trigger.find('.trigger-notification').hide();
        },

        startSession: function () {
            var self = this;

            var userContext = {
                page_type: this.getPageType(),
                page_url: window.location.href,
                referrer: document.referrer,
                user_agent: navigator.userAgent
            };

            $.ajax({
                url: this.options.sessionUrl,
                type: 'POST',
                dataType: 'json',
                data: {
                    user_context: userContext,
                    customer_id: this.options.customerId,
                    store_id: this.options.storeId
                },
                success: function (response) {
                    if (response.session_id) {
                        self.sessionId = response.session_id;
                        
                        if (response.initial_questions && response.initial_questions.length > 0) {
                            self.showQuickReplies(response.initial_questions);
                        }
                    }
                },
                error: function () {
                    console.warn('Failed to start assistant session');
                }
            });
        },

        sendMessage: function (message) {
            var self = this;
            
            message = message || this.chatInput.val().trim();
            
            if (!message || !this.sessionId) {
                return;
            }

            // Add user message to chat
            this.addMessage(message, 'user');
            this.chatInput.val('');

            // Show typing indicator
            this.showTyping();

            // Process message
            $.ajax({
                url: this.options.chatUrl,
                type: 'POST',
                dataType: 'json',
                data: {
                    session_id: this.sessionId,
                    message: message,
                    context: this.getCurrentContext()
                },
                success: function (response) {
                    self.hideTyping();
                    self.handleAssistantResponse(response);
                },
                error: function () {
                    self.hideTyping();
                    self.addMessage('Sorry, I\'m having trouble understanding right now. Please try again.', 'assistant');
                }
            });

            this.trackInteraction('message_sent', { message: message });
        },

        addMessage: function (message, sender, options) {
            options = options || {};
            
            var messageData = {
                message: message,
                timestamp: this.formatTimestamp(new Date()),
                questions: options.questions || []
            };

            var template = sender === 'user' ? this.userMessageTemplate : this.assistantMessageTemplate;
            var messageHtml = template(messageData);
            
            this.chatMessages.append(messageHtml);
            this.scrollToBottom();

            // Store in history
            this.messageHistory.push({
                message: message,
                sender: sender,
                timestamp: new Date(),
                options: options
            });
        },

        handleAssistantResponse: function (response) {
            var message = response.response_text || '';
            var questions = response.questions || [];
            var productSuggestions = response.product_suggestions || [];
            var actions = response.actions || [];

            // Add assistant message
            this.addMessage(message, 'assistant', { questions: questions });

            // Handle product suggestions
            if (productSuggestions.length > 0) {
                this.showProductSuggestions(productSuggestions);
            }

            // Handle specific actions
            if (actions.length > 0) {
                this.handleActions(actions);
            }

            // Hide quick actions if we're in a conversation
            if (this.messageHistory.length > 2) {
                this.quickActions.hide();
            }
        },

        showProductSuggestions: function (products) {
            var self = this;
            var suggestionsHtml = '';

            _.each(products, function (product) {
                suggestionsHtml += self.productSuggestionTemplate(product);
            });

            this.productSuggestions.html(suggestionsHtml).show();
            this.scrollToBottom();
        },

        handleQuickAction: function (action) {
            switch (action) {
                case 'find_product':
                    this.sendMessage('I\'m looking for a specific product. Can you help me find it?');
                    break;
                case 'compare_products':
                    this.sendMessage('I want to compare different products. Can you help?');
                    break;
                case 'get_recommendations':
                    this.sendMessage('Can you recommend some products for me?');
                    break;
            }
        },

        handleActions: function (actions) {
            var self = this;

            _.each(actions, function (action) {
                switch (action.type) {
                    case 'start_guided_flow':
                        self.startGuidedFlow(action.flow_type);
                        break;
                    case 'show_products':
                        self.showProductSuggestions(action.products);
                        break;
                    case 'redirect':
                        window.location.href = action.url;
                        break;
                }
            });
        },

        startGuidedFlow: function (flowType) {
            var self = this;

            $.ajax({
                url: this.options.flowUrl,
                type: 'GET',
                dataType: 'json',
                data: {
                    flow_type: flowType,
                    store_id: this.options.storeId
                },
                success: function (response) {
                    if (response.questions && response.questions.length > 0) {
                        self.currentFlow = flowType;
                        self.flowStep = 0;
                        self.flowAnswers = {};
                        self.showGuidedFlow(response);
                    }
                },
                error: function () {
                    self.addMessage('Sorry, I couldn\'t load the guided flow right now.', 'assistant');
                }
            });
        },

        showGuidedFlow: function (flowData) {
            var self = this;
            
            // Update progress
            var progressPercent = ((this.flowStep + 1) / flowData.total_steps) * 100;
            this.guidedFlow.find('.progress-fill').css('width', progressPercent + '%');
            this.guidedFlow.find('.progress-text').text('Step ' + (this.flowStep + 1) + ' of ' + flowData.total_steps);

            // Show current question
            var currentQuestion = flowData.questions[this.flowStep];
            if (currentQuestion) {
                var questionHtml = this.guidedFlowQuestionTemplate(currentQuestion);
                this.guidedFlow.find('#flow-content').html(questionHtml);
                this.guidedFlow.show();
                this.scrollToBottom();
            }
        },

        processFlowStep: function () {
            var self = this;
            var questionContainer = this.guidedFlow.find('.flow-question');
            var questionId = questionContainer.data('question-id');
            var answer = this.getFlowAnswer(questionContainer);

            if (answer !== null) {
                this.flowAnswers[questionId] = answer;
                this.flowStep++;

                // Continue flow or submit
                this.continueGuidedFlow();
            }
        },

        getFlowAnswer: function (questionContainer) {
            var questionType = questionContainer.find('input, select').first().attr('type') || 'text';
            
            switch (questionType) {
                case 'radio':
                    return questionContainer.find('input:checked').val() || null;
                case 'text':
                    return questionContainer.find('.question-input').val() || null;
                case 'range':
                    return questionContainer.find('input[type="range"]').val() || null;
                default:
                    return null;
            }
        },

        continueGuidedFlow: function () {
            var self = this;

            // Submit current answers to get next step or results
            $.ajax({
                url: this.options.flowUrl,
                type: 'POST',
                dataType: 'json',
                data: {
                    flow_type: this.currentFlow,
                    answers: this.flowAnswers,
                    current_step: this.flowStep,
                    store_id: this.options.storeId
                },
                success: function (response) {
                    if (response.completed) {
                        // Flow completed, show results
                        self.guidedFlow.hide();
                        if (response.recommendations) {
                            self.showProductSuggestions(response.recommendations);
                        }
                        if (response.explanation) {
                            self.addMessage(response.explanation, 'assistant');
                        }
                    } else if (response.questions && response.questions.length > 0) {
                        // Continue with next step
                        self.showGuidedFlow(response);
                    }
                },
                error: function () {
                    self.addMessage('Sorry, there was an error processing your answers.', 'assistant');
                }
            });
        },

        skipFlowStep: function () {
            this.flowStep++;
            this.continueGuidedFlow();
        },

        showTyping: function () {
            this.typingIndicator.show();
            this.scrollToBottom();
        },

        hideTyping: function () {
            this.typingIndicator.hide();
        },

        scrollToBottom: function () {
            var chatContainer = this.chatMessages.parent();
            chatContainer.scrollTop(chatContainer[0].scrollHeight);
        },

        getCurrentContext: function () {
            return {
                page_type: this.getPageType(),
                page_url: window.location.href,
                message_count: this.messageHistory.length,
                flow_active: this.currentFlow !== null
            };
        },

        getPageType: function () {
            var url = window.location.pathname;
            
            if (url.includes('/product/')) {
                return 'product';
            } else if (url.includes('/category/') || url.includes('.html')) {
                return 'category';
            } else if (url.includes('/checkout/cart/')) {
                return 'cart';
            } else if (url.includes('/checkout/')) {
                return 'checkout';
            } else if (url === '/' || url === '/index.php') {
                return 'homepage';
            } else {
                return 'other';
            }
        },

        formatTimestamp: function (date) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        },

        trackInteraction: function (interactionType, data) {
            if (!this.options.trackingUrl || !this.sessionId) {
                return;
            }

            $.ajax({
                url: this.options.trackingUrl,
                type: 'POST',
                dataType: 'json',
                data: {
                    session_id: this.sessionId,
                    interaction_type: interactionType,
                    interaction_data: data || {},
                    timestamp: new Date().toISOString()
                },
                async: true
            });
        },

        _destroy: function () {
            if (this.sessionId) {
                // End session
                $.ajax({
                    url: this.options.sessionUrl,
                    type: 'DELETE',
                    data: { session_id: this.sessionId },
                    async: false
                });
            }
        }
    });

    return $.discovery.discoveryAssistant;
});