/**
 * AI Discovery Suite Admin Configuration JavaScript
 */
define([
    'jquery',
    'Magento_Ui/js/modal/alert',
    'mage/url',
    'loader'
], function ($, alert, url, loader) {
    'use strict';

    return {
        /**
         * Initialize admin configuration
         */
        init: function () {
            this.bindEvents();
            this.checkServiceStatus();
        },

        /**
         * Bind UI events
         */
        bindEvents: function () {
            var self = this;

            // Test connection button
            $(document).on('click', '.discovery-suite-test-button', function (e) {
                e.preventDefault();
                self.testConnection();
            });

            // Enable/disable features based on main toggle
            $(document).on('change', '#discovery_suite_general_enabled', function () {
                self.toggleFeatureSections($(this).val());
            });
        },

        /**
         * Test API connection
         */
        testConnection: function () {
            var self = this;
            var testUrl = url.build('discovery/admin/test');

            $('body').loader('show');

            $.ajax({
                url: testUrl,
                type: 'POST',
                dataType: 'json',
                success: function (response) {
                    $('body').loader('hide');
                    
                    if (response.success) {
                        self.showServiceStatus(response.services);
                        alert({
                            title: 'Connection Test Results',
                            content: 'Successfully connected to ' + response.connected + ' out of ' + response.total + ' services.'
                        });
                    } else {
                        alert({
                            title: 'Connection Failed',
                            content: response.message || 'Unable to connect to AI services.'
                        });
                    }
                },
                error: function () {
                    $('body').loader('hide');
                    alert({
                        title: 'Test Failed',
                        content: 'Unable to perform connection test.'
                    });
                }
            });
        },

        /**
         * Check initial service status
         */
        checkServiceStatus: function () {
            // Add service status indicators
            this.addServiceStatusIndicators();
        },

        /**
         * Add service status indicators
         */
        addServiceStatusIndicators: function () {
            var services = [
                { name: 'Search Service', port: '7001' },
                { name: 'Recommendation Service', port: '7002' },
                { name: 'Analytics Service', port: '7003' },
                { name: 'Shopping Assistant', port: '7004' }
            ];

            var statusHtml = '<div class="discovery-suite-config"><h3>Service Status</h3>';
            
            services.forEach(function (service) {
                statusHtml += '<div class="discovery-suite-service-check" id="service-' + service.port + '">';
                statusHtml += '<strong>' + service.name + '</strong> (Port ' + service.port + ') - ';
                statusHtml += '<span class="status-indicator">Checking...</span>';
                statusHtml += '</div>';
            });

            statusHtml += '<button type="button" class="discovery-suite-test-button">Test All Connections</button>';
            statusHtml += '</div>';

            // Insert after the general section
            $('#discovery_suite_general-head').after(statusHtml);
        },

        /**
         * Show service status results
         */
        showServiceStatus: function (services) {
            if (!services) return;

            Object.keys(services).forEach(function (servicePort) {
                var service = services[servicePort];
                var element = $('#service-' + servicePort);
                var statusSpan = element.find('.status-indicator');

                if (service.connected) {
                    element.removeClass('error').addClass('success');
                    statusSpan.text('Connected (' + service.response_time + 'ms)');
                } else {
                    element.removeClass('success').addClass('error');
                    statusSpan.text('Failed: ' + service.error);
                }
            });
        },

        /**
         * Toggle feature sections based on main enable/disable
         */
        toggleFeatureSections: function (enabled) {
            var sections = ['search', 'recommendations', 'analytics', 'assistant'];
            
            sections.forEach(function (section) {
                var sectionElement = $('#discovery_suite_' + section);
                if (enabled === '1') {
                    sectionElement.show();
                } else {
                    sectionElement.hide();
                }
            });
        }
    };
});