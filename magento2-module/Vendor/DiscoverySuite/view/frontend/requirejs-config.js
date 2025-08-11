/**
 * AI Discovery Suite RequireJS Configuration
 */
var config = {
    map: {
        '*': {
            'discoveryAutocomplete': 'Vendor_DiscoverySuite/js/components/autocomplete',
            'discoveryRecommendations': 'Vendor_DiscoverySuite/js/components/recommendations',
            'discoveryAssistant': 'Vendor_DiscoverySuite/js/components/assistant',
            'discoveryAnalytics': 'Vendor_DiscoverySuite/js/components/analytics',
            'discoveryMain': 'Vendor_DiscoverySuite/js/discovery-suite'
        }
    },
    shim: {
        'Vendor_DiscoverySuite/js/discovery-suite': {
            deps: ['jquery']
        }
    }
};