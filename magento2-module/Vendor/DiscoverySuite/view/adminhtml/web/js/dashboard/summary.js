/**
 * DiscoverySuite Admin Dashboard Summary Component
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

define([
    'uiComponent',
    'ko',
    'jquery',
    'mage/url'
], function (Component, ko, $, urlBuilder) {
    'use strict';

    return Component.extend({
        defaults: {
            template: 'Vendor_DiscoverySuite/dashboard/summary',
            totalRecords: 0,
            summaryData: {},
            isLoading: false,
            refreshInterval: 30000 // 30 seconds
        },

        /**
         * Initialize component
         */
        initialize: function () {
            this._super();
            
            this.totalRecords = ko.observable(this.totalRecords);
            this.summaryData = ko.observable(this.summaryData);
            this.isLoading = ko.observable(false);
            
            this.loadSummaryData();
            this.startAutoRefresh();
            
            return this;
        },

        /**
         * Initialize observables
         */
        initObservable: function () {
            this._super()
                .observe([
                    'totalRecords',
                    'summaryData',
                    'isLoading'
                ]);

            return this;
        },

        /**
         * Load summary data from API
         */
        loadSummaryData: function () {
            var self = this;
            
            this.isLoading(true);
            
            $.ajax({
                url: urlBuilder.build('discovery/analytics/summary'),
                type: 'GET',
                dataType: 'json',
                success: function (response) {
                    if (response.success) {
                        self.summaryData(response.data);
                    }
                },
                error: function () {
                    console.error('Failed to load analytics summary');
                },
                complete: function () {
                    self.isLoading(false);
                }
            });
        },

        /**
         * Start auto-refresh timer
         */
        startAutoRefresh: function () {
            var self = this;
            
            setInterval(function () {
                self.loadSummaryData();
            }, this.refreshInterval);
        },

        /**
         * Get formatted number
         */
        formatNumber: function (number) {
            if (!number) return '0';
            
            return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        },

        /**
         * Get percentage with sign
         */
        formatPercentage: function (percentage, showSign) {
            if (!percentage) return '0%';
            
            var formatted = parseFloat(percentage).toFixed(1) + '%';
            
            if (showSign && percentage > 0) {
                formatted = '+' + formatted;
            }
            
            return formatted;
        },

        /**
         * Get trend CSS class
         */
        getTrendClass: function (value) {
            if (!value) return 'neutral';
            
            return value > 0 ? 'positive' : 'negative';
        },

        /**
         * Get metric cards data
         */
        getMetricCards: function () {
            var data = this.summaryData();
            
            return [
                {
                    title: 'Total Events',
                    value: this.formatNumber(data.total_events || 0),
                    change: this.formatPercentage(data.events_change, true),
                    trend: this.getTrendClass(data.events_change),
                    icon: 'icon-activity'
                },
                {
                    title: 'Active Users',
                    value: this.formatNumber(data.active_users || 0),
                    change: this.formatPercentage(data.users_change, true),
                    trend: this.getTrendClass(data.users_change),
                    icon: 'icon-users'
                },
                {
                    title: 'Search Queries',
                    value: this.formatNumber(data.search_queries || 0),
                    change: this.formatPercentage(data.search_change, true),
                    trend: this.getTrendClass(data.search_change),
                    icon: 'icon-search'
                },
                {
                    title: 'Recommendations Served',
                    value: this.formatNumber(data.recommendations_served || 0),
                    change: this.formatPercentage(data.recommendations_change, true),
                    trend: this.getTrendClass(data.recommendations_change),
                    icon: 'icon-target'
                },
                {
                    title: 'Conversion Rate',
                    value: this.formatPercentage(data.conversion_rate),
                    change: this.formatPercentage(data.conversion_change, true),
                    trend: this.getTrendClass(data.conversion_change),
                    icon: 'icon-trending-up'
                },
                {
                    title: 'Average Session Duration',
                    value: this.formatDuration(data.avg_session_duration || 0),
                    change: this.formatPercentage(data.duration_change, true),
                    trend: this.getTrendClass(data.duration_change),
                    icon: 'icon-clock'
                }
            ];
        },

        /**
         * Format duration in seconds to human readable
         */
        formatDuration: function (seconds) {
            if (!seconds) return '0s';
            
            var minutes = Math.floor(seconds / 60);
            var remainingSeconds = Math.floor(seconds % 60);
            
            if (minutes > 0) {
                return minutes + 'm ' + remainingSeconds + 's';
            }
            
            return remainingSeconds + 's';
        },

        /**
         * Get top performing metrics
         */
        getTopMetrics: function () {
            var data = this.summaryData();
            
            return {
                top_searches: data.top_searches || [],
                top_products: data.top_products || [],
                top_categories: data.top_categories || []
            };
        },

        /**
         * Refresh data manually
         */
        refresh: function () {
            this.loadSummaryData();
        },

        /**
         * Export summary report
         */
        exportReport: function () {
            window.open(urlBuilder.build('discovery/analytics/export'), '_blank');
        }
    });
});