/**
 * Discovery Suite Session Management Utility
 * Provides consistent session ID management across all widgets
 */
define([
    'jquery'
], function ($) {
    'use strict';

    return {
        /**
         * Get or create a session ID
         * @return {string}
         */
        getSessionId: function() {
            var sessionId = sessionStorage.getItem('discovery_session_id');
            if (!sessionId) {
                sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                sessionStorage.setItem('discovery_session_id', sessionId);
            }
            return sessionId;
        },

        /**
         * Get user ID from customer data
         * @return {string|null}
         */
        getUserId: function() {
            // Try to get from global customer data
            if (window.customerData && window.customerData.get && window.customerData.get('customer')) {
                var customer = window.customerData.get('customer')();
                return customer && customer.id ? customer.id.toString() : null;
            }
            
            // Fallback to global variables
            return window.userId || window.customerId || null;
        },

        /**
         * Get analytics session ID (separate from main session)
         * @return {string}
         */
        getAnalyticsSessionId: function() {
            var sessionId = sessionStorage.getItem('discovery_analytics_session');
            if (!sessionId) {
                sessionId = 'analytics_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                sessionStorage.setItem('discovery_analytics_session', sessionId);
            }
            return sessionId;
        },

        /**
         * Store recently viewed products
         * @param {Array} products
         */
        setViewedProducts: function(products) {
            sessionStorage.setItem('recently_viewed_products', JSON.stringify(products));
        },

        /**
         * Get recently viewed products
         * @return {Array}
         */
        getViewedProducts: function() {
            var viewed = sessionStorage.getItem('recently_viewed_products');
            return viewed ? JSON.parse(viewed) : [];
        },

        /**
         * Get user ID (works for both logged in and anonymous users)
         * @return {string}
         */
        getUserId: function() {
            // Try to get user ID from customer data
            if (window.customerData && window.customerData.get) {
                try {
                    var customer = window.customerData.get('customer')();
                    if (customer && customer.id) {
                        return customer.id.toString();
                    }
                } catch (e) {
                    // Ignore errors, fallback to anonymous
                }
            }
            
            // Try global variables
            if (window.userId && window.userId !== 'undefined') {
                return window.userId.toString();
            }
            if (window.customerId && window.customerId !== 'undefined') {
                return window.customerId.toString();
            }
            
            // For anonymous users, use session-based ID
            var anonymousId = sessionStorage.getItem('discovery_anonymous_id');
            if (!anonymousId) {
                anonymousId = 'anon_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                sessionStorage.setItem('discovery_anonymous_id', anonymousId);
            }
            return anonymousId;
        },

        /**
         * Clear all discovery session data
         */
        clearSessionData: function() {
            sessionStorage.removeItem('discovery_session_id');
            sessionStorage.removeItem('discovery_analytics_session');
            sessionStorage.removeItem('discovery_anonymous_id');
            sessionStorage.removeItem('recently_viewed_products');
            sessionStorage.removeItem('came_from_search');
            sessionStorage.removeItem('last_search_query');
        }
    };
});
