/**
 * DiscoverySuite Autocomplete Widget
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
    'jquery/ui'
], function ($, _, mageTemplate) {
    'use strict';

    $.widget('discovery.discoveryAutocomplete', {
        options: {
            enabled: true,
            minChars: 2,
            maxResults: 10,
            url: '',
            delay: 300,
            showProducts: true,
            showCategories: true,
            showSuggestions: true,
            template: '#discovery-autocomplete-template'
        },

        _create: function () {
            if (!this.options.enabled) {
                return;
            }

            this.searchInput = this.element.find('#discovery-search');
            this.autocompleteContainer = this.element.find('#discovery-search-autocomplete');
            this.searchForm = this.element.find('#discovery-search-form');
            
            this.template = mageTemplate($(this.options.template).html());
            this.currentRequest = null;
            this.selectedIndex = -1;
            this.cache = {};

            this._bindEvents();
        },

        _bindEvents: function () {
            var self = this;

            // Input events
            this.searchInput.on('input.discovery', _.debounce(function (e) {
                self._onInput(e);
            }, this.options.delay));

            this.searchInput.on('keydown.discovery', function (e) {
                self._onKeyDown(e);
            });

            this.searchInput.on('focus.discovery', function (e) {
                self._onFocus(e);
            });

            this.searchInput.on('blur.discovery', function (e) {
                // Delay hiding to allow clicking on suggestions
                setTimeout(function () {
                    self._hideSuggestions();
                }, 200);
            });

            // Autocomplete container events
            this.autocompleteContainer.on('click.discovery', '.suggestion-item', function (e) {
                e.preventDefault();
                var suggestion = $(this).data('suggestion');
                self._selectSuggestion(suggestion);
            });

            this.autocompleteContainer.on('click.discovery', '.product-link', function (e) {
                var productId = $(this).closest('.product-item').data('product-id');
                var productName = $(this).find('.product-name').text().trim();
                var position = $(this).closest('.product-item').index();
                
                // Track search click for personalization
                self._trackSearchClick(productId, productName, position);
                
                // Track general click
                self._trackClick('product', productId);
                
                // Set flag that user is coming from search
                sessionStorage.setItem('came_from_search', 'true');
                sessionStorage.setItem('last_search_query', self.searchInput.val().trim());
            });

            this.autocompleteContainer.on('click.discovery', '.category-link', function (e) {
                var categoryName = $(this).find('.category-name').text();
                self._trackClick('category', categoryName);
            });

            this.autocompleteContainer.on('click.discovery', '.spell-suggestion', function (e) {
                e.preventDefault();
                var suggestion = $(this).data('suggestion');
                self._selectSuggestion(suggestion);
            });

            // Form submission
            this.searchForm.on('submit.discovery', function (e) {
                var query = self.searchInput.val().trim();
                if (query) {
                    self._trackSearch(query);
                }
            });

            // Click outside to hide
            $(document).on('click.discovery', function (e) {
                if (!self.element.is(e.target) && self.element.has(e.target).length === 0) {
                    self._hideSuggestions();
                }
            });
        },

        _onInput: function (e) {
            var query = this.searchInput.val().trim();
            
            if (query.length >= this.options.minChars) {
                this._getSuggestions(query);
            } else {
                this._hideSuggestions();
            }
        },

        _onKeyDown: function (e) {
            var suggestions = this.autocompleteContainer.find('.suggestion-item, .product-item, .category-item');
            
            switch (e.keyCode) {
                case 38: // Arrow up
                    e.preventDefault();
                    this._navigateUp(suggestions);
                    break;
                case 40: // Arrow down
                    e.preventDefault();
                    this._navigateDown(suggestions);
                    break;
                case 13: // Enter
                    if (this.selectedIndex >= 0 && suggestions.length > 0) {
                        e.preventDefault();
                        this._selectCurrentItem(suggestions);
                    }
                    break;
                case 27: // Escape
                    this._hideSuggestions();
                    this.searchInput.blur();
                    break;
            }
        },

        _onFocus: function (e) {
            var query = this.searchInput.val().trim();
            if (query.length >= this.options.minChars) {
                this._getSuggestions(query);
            }
        },

        _navigateUp: function (suggestions) {
            if (this.selectedIndex > 0) {
                this.selectedIndex--;
            } else {
                this.selectedIndex = suggestions.length - 1;
            }
            this._highlightItem(suggestions);
        },

        _navigateDown: function (suggestions) {
            if (this.selectedIndex < suggestions.length - 1) {
                this.selectedIndex++;
            } else {
                this.selectedIndex = 0;
            }
            this._highlightItem(suggestions);
        },

        _highlightItem: function (suggestions) {
            suggestions.removeClass('selected');
            if (this.selectedIndex >= 0 && this.selectedIndex < suggestions.length) {
                $(suggestions[this.selectedIndex]).addClass('selected');
            }
        },

        _selectCurrentItem: function (suggestions) {
            if (this.selectedIndex >= 0 && this.selectedIndex < suggestions.length) {
                var selected = $(suggestions[this.selectedIndex]);
                
                if (selected.hasClass('suggestion-item')) {
                    var suggestion = selected.data('suggestion');
                    this._selectSuggestion(suggestion);
                } else if (selected.hasClass('product-item')) {
                    var link = selected.find('.product-link');
                    if (link.length) {
                        window.location.href = link.attr('href');
                    }
                } else if (selected.hasClass('category-item')) {
                    var link = selected.find('.category-link');
                    if (link.length) {
                        window.location.href = link.attr('href');
                    }
                }
            }
        },

        _selectSuggestion: function (suggestion) {
            this.searchInput.val(suggestion);
            this._hideSuggestions();
            this.searchForm.submit();
        },

        _getSuggestions: function (query) {
            var self = this;

            // Check cache first
            if (this.cache[query]) {
                this._showSuggestions(this.cache[query]);
                return;
            }

            // Cancel previous request
            if (this.currentRequest) {
                this.currentRequest.abort();
            }

            // Show loading state
            this._showLoading();

            // Make new request
            this.currentRequest = $.ajax({
                url: this.options.url,
                type: 'GET',
                dataType: 'json',
                data: {
                    q: query,
                    limit: this.options.maxResults,
                    user_id: this._getUserId(),
                    session_id: this._getSessionId()
                },
                success: function (data) {
                    self.currentRequest = null;
                    
                    // Cache the results
                    self.cache[query] = data;
                    
                    // Show suggestions
                    self._showSuggestions(data);
                },
                error: function (xhr, status, error) {
                    self.currentRequest = null;
                    
                    if (status !== 'abort') {
                        console.warn('Autocomplete request failed:', error);
                        self._hideSuggestions();
                    }
                }
            });
        },

        _showLoading: function () {
            this.autocompleteContainer.html('<div class="loading">Searching...</div>').show();
        },

        _showSuggestions: function (data) {
            if (!data || (!data.suggestions && !data.products && !data.categories)) {
                this._hideSuggestions();
                return;
            }

            var html = this.template({ data: data });
            this.autocompleteContainer.html(html).show();
            this.selectedIndex = -1;

            // Track autocomplete display
            this._trackAutocomplete(this.searchInput.val(), data);
        },

        _hideSuggestions: function () {
            this.autocompleteContainer.hide();
            this.selectedIndex = -1;
        },

        _trackSearch: function (query) {
            // Track search event
            if (window.discoveryAnalytics) {
                window.discoveryAnalytics.track('search', {
                    query: query,
                    source: 'autocomplete'
                });
            }
        },

        _trackAutocomplete: function (query, data) {
            // Track autocomplete display
            if (window.discoveryAnalytics) {
                window.discoveryAnalytics.track('autocomplete_shown', {
                    query: query,
                    suggestion_count: data.suggestions ? data.suggestions.length : 0,
                    product_count: data.products ? data.products.length : 0,
                    category_count: data.categories ? data.categories.length : 0
                });
            }
        },

        _trackClick: function (type, identifier) {
            // Track click event
            if (window.discoveryAnalytics) {
                window.discoveryAnalytics.track('autocomplete_click', {
                    type: type,
                    identifier: identifier,
                    query: this.searchInput.val()
                });
            }
        },

        _trackSearchClick: function (productId, productName, position) {
            // Track search click for personalization
            var trackingData = {
                user_id: this._getUserId(),
                session_id: this._getSessionId(),
                search_query: this.searchInput.val().trim(),
                clicked_product_id: productId.toString(),
                clicked_product_name: productName,
                position_in_results: position
            };
            
            // Send to backend API
            $.ajax({
                url: 'http://localhost:7001/api/v1/tracking/search-click',
                type: 'POST',
                data: JSON.stringify(trackingData),
                contentType: 'application/json',
                success: function(response) {
                    console.log('Search click tracked:', response);
                },
                error: function(xhr, status, error) {
                    console.warn('Failed to track search click:', error);
                }
            });
        },

        _getUserId: function () {
            // Try to get user ID from customer data or global variables
            if (window.customerData && window.customerData.get && window.customerData.get('customer')) {
                var customer = window.customerData.get('customer')();
                return customer && customer.id ? customer.id.toString() : null;
            }
            
            // Fallback to global variables
            return window.userId || window.customerId || null;
        },

        _getSessionId: function () {
            // Generate or get session ID from storage
            var sessionId = sessionStorage.getItem('discovery_session_id');
            
            if (!sessionId) {
                // Generate new session ID
                sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                sessionStorage.setItem('discovery_session_id', sessionId);
            }
            
            return sessionId;
        },

        _destroy: function () {
            this.searchInput.off('.discovery');
            this.autocompleteContainer.off('.discovery');
            this.searchForm.off('.discovery');
            $(document).off('.discovery');
            
            if (this.currentRequest) {
                this.currentRequest.abort();
            }
        }
    });

    return $.discovery.discoveryAutocomplete;
});