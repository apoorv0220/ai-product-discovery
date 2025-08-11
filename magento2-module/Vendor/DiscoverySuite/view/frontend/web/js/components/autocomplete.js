/**
 * AI Search Autocomplete Widget
 */
define([
    'jquery',
    'mage/url',
    'mage/template'
], function ($, url, mageTemplate) {
    'use strict';

    $.widget('discovery.discoveryAutocomplete', {
        options: {
            enabled: true,
            minSearchLength: 2,
            delay: 300,
            maxSuggestions: 10,
            endpoint: '',
            showImages: true,
            showPrices: true,
            showCategories: true
        },

        _create: function () {
            if (!this.options.enabled) {
                return;
            }

            this.searchInput = this.element;
            this.resultsContainer = $('#discovery-autocomplete-results');
            this.searchTimeout = null;
            this.activeIndex = -1;

            this._bindEvents();
        },

        _bindEvents: function () {
            var self = this;

            this.searchInput.on('input.autocomplete', function () {
                self._onInput();
            });

            this.searchInput.on('keydown.autocomplete', function (e) {
                self._onKeydown(e);
            });

            this.searchInput.on('focus.autocomplete', function () {
                if (self.resultsContainer.children().length > 0) {
                    self.resultsContainer.show();
                }
            });

            $(document).on('click.autocomplete', function (e) {
                if (!$(e.target).closest(self.searchInput).length && 
                    !$(e.target).closest(self.resultsContainer).length) {
                    self.resultsContainer.hide();
                }
            });
        },

        _onInput: function () {
            var self = this;
            var query = this.searchInput.val().trim();

            clearTimeout(this.searchTimeout);

            if (query.length < this.options.minSearchLength) {
                this.resultsContainer.hide();
                return;
            }

            this.searchTimeout = setTimeout(function () {
                self._fetchSuggestions(query);
            }, this.options.delay);
        },

        _onKeydown: function (e) {
            var items = this.resultsContainer.find('.discovery-autocomplete-item');
            
            switch (e.keyCode) {
                case 40: // Down arrow
                    e.preventDefault();
                    this._moveSelection(1, items);
                    break;
                case 38: // Up arrow
                    e.preventDefault();
                    this._moveSelection(-1, items);
                    break;
                case 13: // Enter
                    if (this.activeIndex >= 0) {
                        e.preventDefault();
                        this._selectItem(items.eq(this.activeIndex));
                    }
                    break;
                case 27: // Escape
                    this.resultsContainer.hide();
                    this.activeIndex = -1;
                    break;
            }
        },

        _moveSelection: function (direction, items) {
            items.removeClass('active');
            
            if (direction > 0) {
                this.activeIndex = Math.min(this.activeIndex + 1, items.length - 1);
            } else {
                this.activeIndex = Math.max(this.activeIndex - 1, -1);
            }

            if (this.activeIndex >= 0) {
                items.eq(this.activeIndex).addClass('active');
            }
        },

        _selectItem: function (item) {
            var url = item.data('url');
            if (url) {
                window.location.href = url;
            }
        },

        _fetchSuggestions: function (query) {
            var self = this;

            $.ajax({
                url: this.options.endpoint,
                type: 'GET',
                data: {
                    q: query,
                    limit: this.options.maxSuggestions
                },
                success: function (response) {
                    if (response.success && response.suggestions) {
                        self._displaySuggestions(response.suggestions);
                    }
                },
                error: function () {
                    self.resultsContainer.hide();
                }
            });
        },

        _displaySuggestions: function (suggestions) {
            var html = '';
            var self = this;

            $.each(suggestions, function (index, suggestion) {
                html += self._renderSuggestion(suggestion, index);
            });

            this.resultsContainer.html(html).show();
            this.activeIndex = -1;

            // Bind click events
            this.resultsContainer.find('.discovery-autocomplete-item').on('click', function () {
                self._selectItem($(this));
            });
        },

        _renderSuggestion: function (suggestion, index) {
            var html = '<div class="discovery-autocomplete-item" data-index="' + index + '"';
            
            if (suggestion.url) {
                html += ' data-url="' + suggestion.url + '"';
            }
            
            html += '>';

            if (this.options.showImages && suggestion.image) {
                html += '<img src="' + suggestion.image + '" class="discovery-autocomplete-image" alt="' + suggestion.title + '">';
            }

            html += '<div class="discovery-autocomplete-details">';
            html += '<div class="discovery-autocomplete-title">' + suggestion.title + '</div>';

            if (this.options.showPrices && suggestion.price) {
                html += '<div class="discovery-autocomplete-price">' + suggestion.price + '</div>';
            }

            if (suggestion.category) {
                html += '<div class="discovery-autocomplete-category">' + suggestion.category + '</div>';
            }

            html += '</div></div>';

            return html;
        },

        _destroy: function () {
            this.searchInput.off('.autocomplete');
            $(document).off('.autocomplete');
            clearTimeout(this.searchTimeout);
        }
    });

    return $.discovery.discoveryAutocomplete;
});