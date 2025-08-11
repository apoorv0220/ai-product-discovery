<?php
/**
 * DiscoverySuite Helper Data
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Helper;

use Magento\Framework\App\Helper\AbstractHelper;
use Magento\Framework\App\Helper\Context;
use Magento\Store\Model\ScopeInterface;

class Data extends AbstractHelper
{
    const XML_PATH_ENABLED = 'discovery_suite_config/general/enabled';
    const XML_PATH_API_BASE_URL = 'discovery_suite_config/general/api_base_url';
    const XML_PATH_API_KEY = 'discovery_suite_config/general/api_key';
    const XML_PATH_TIMEOUT = 'discovery_suite_config/general/timeout';
    const XML_PATH_DEBUG_MODE = 'discovery_suite_config/general/debug_mode';
    
    // Advanced Search Configuration
    const XML_PATH_SEARCH_ENABLED = 'discovery_suite_config/search/enabled';
    const XML_PATH_AUTOCOMPLETE_ENABLED = 'discovery_suite_config/search/autocomplete_enabled';
    const XML_PATH_NLP_ENABLED = 'discovery_suite_config/search/nlp_enabled';
    const XML_PATH_TYPO_TOLERANCE = 'discovery_suite_config/search/typo_tolerance';
    const XML_PATH_INTENT_RECOGNITION = 'discovery_suite_config/search/intent_recognition';
    const XML_PATH_SEMANTIC_SEARCH = 'discovery_suite_config/search/semantic_search';
    
    // ML Recommendations Configuration
    const XML_PATH_RECOMMENDATIONS_ENABLED = 'discovery_suite_config/recommendations/enabled';
    const XML_PATH_ML_POWERED = 'discovery_suite_config/recommendations/ml_powered';
    const XML_PATH_REAL_TIME_LEARNING = 'discovery_suite_config/recommendations/real_time_learning';
    const XML_PATH_COLLABORATIVE_FILTERING = 'discovery_suite_config/recommendations/collaborative_filtering';
    const XML_PATH_CONTENT_BASED = 'discovery_suite_config/recommendations/content_based';
    
    // Conversational AI Configuration
    const XML_PATH_SHOPPING_ASSISTANT_ENABLED = 'discovery_suite_config/shopping_assistant/enabled';
    const XML_PATH_CONVERSATIONAL_AI = 'discovery_suite_config/shopping_assistant/conversational_ai';
    const XML_PATH_NLP_PROCESSING = 'discovery_suite_config/shopping_assistant/nlp_processing';
    const XML_PATH_MULTI_TURN_CONVERSATIONS = 'discovery_suite_config/shopping_assistant/multi_turn_conversations';
    
    // Advanced Analytics Configuration
    const XML_PATH_ANALYTICS_ENABLED = 'discovery_suite_config/analytics/enabled';
    const XML_PATH_REAL_TIME_TRACKING = 'discovery_suite_config/analytics/real_time_tracking';
    const XML_PATH_BEHAVIORAL_INSIGHTS = 'discovery_suite_config/analytics/behavioral_insights';
    const XML_PATH_AB_TESTING = 'discovery_suite_config/analytics/ab_testing';
    const XML_PATH_PREDICTIVE_ANALYTICS = 'discovery_suite_config/analytics/predictive_analytics';

    /**
     * @var array
     */
    private $servicePorts = [
        'search' => 7001,
        'recommendation' => 7002,
        'listing_optimizer' => 7003,
        'analytics' => 7003,
        'shopping_assistant' => 7004
    ];

    /**
     * Constructor
     *
     * @param Context $context
     */
    public function __construct(Context $context)
    {
        parent::__construct($context);
    }

    /**
     * Check if module is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isEnabled($storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_ENABLED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    // ========================================
    // ADVANCED SEARCH FEATURE METHODS
    // ========================================

    /**
     * Check if NLP processing is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isNlpEnabled($storeId = null): bool
    {
        return $this->isSearchEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_NLP_ENABLED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if typo tolerance is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isTypoToleranceEnabled($storeId = null): bool
    {
        return $this->isSearchEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_TYPO_TOLERANCE,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if intent recognition is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isIntentRecognitionEnabled($storeId = null): bool
    {
        return $this->isSearchEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_INTENT_RECOGNITION,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if semantic search is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isSemanticSearchEnabled($storeId = null): bool
    {
        return $this->isSearchEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_SEMANTIC_SEARCH,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    // ========================================
    // ML RECOMMENDATIONS FEATURE METHODS
    // ========================================

    /**
     * Check if ML-powered recommendations are enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isMlPoweredRecommendationsEnabled($storeId = null): bool
    {
        return $this->isRecommendationsEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_ML_POWERED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if real-time learning is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isRealTimeLearningEnabled($storeId = null): bool
    {
        return $this->isRecommendationsEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_REAL_TIME_LEARNING,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if collaborative filtering is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isCollaborativeFilteringEnabled($storeId = null): bool
    {
        return $this->isRecommendationsEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_COLLABORATIVE_FILTERING,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if content-based recommendations are enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isContentBasedEnabled($storeId = null): bool
    {
        return $this->isRecommendationsEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_CONTENT_BASED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    // ========================================
    // CONVERSATIONAL AI FEATURE METHODS
    // ========================================

    /**
     * Check if shopping assistant is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isShoppingAssistantEnabled($storeId = null): bool
    {
        return $this->isEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_SHOPPING_ASSISTANT_ENABLED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if conversational AI is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isConversationalAiEnabled($storeId = null): bool
    {
        return $this->isShoppingAssistantEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_CONVERSATIONAL_AI,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if NLP processing for chat is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isChatNlpEnabled($storeId = null): bool
    {
        return $this->isShoppingAssistantEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_NLP_PROCESSING,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if multi-turn conversations are enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isMultiTurnConversationsEnabled($storeId = null): bool
    {
        return $this->isShoppingAssistantEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_MULTI_TURN_CONVERSATIONS,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    // ========================================
    // ADVANCED ANALYTICS FEATURE METHODS
    // ========================================

    /**
     * Check if real-time tracking is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isRealTimeTrackingEnabled($storeId = null): bool
    {
        return $this->isAnalyticsEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_REAL_TIME_TRACKING,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if behavioral insights are enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isBehavioralInsightsEnabled($storeId = null): bool
    {
        return $this->isAnalyticsEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_BEHAVIORAL_INSIGHTS,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if A/B testing is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isAbTestingEnabled($storeId = null): bool
    {
        return $this->isAnalyticsEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_AB_TESTING,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if predictive analytics are enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isPredictiveAnalyticsEnabled($storeId = null): bool
    {
        return $this->isAnalyticsEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_PREDICTIVE_ANALYTICS,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Get API base URL
     *
     * @param int|null $storeId
     * @return string
     */
    public function getApiBaseUrl($storeId = null): string
    {
        return (string)$this->scopeConfig->getValue(
            self::XML_PATH_API_BASE_URL,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Get API key
     *
     * @param int|null $storeId
     * @return string
     */
    public function getApiKey($storeId = null): string
    {
        return (string)$this->scopeConfig->getValue(
            self::XML_PATH_API_KEY,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Get API timeout
     *
     * @param int|null $storeId
     * @return int
     */
    public function getTimeout($storeId = null): int
    {
        return (int)$this->scopeConfig->getValue(
            self::XML_PATH_TIMEOUT,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if debug mode is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isDebugMode($storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_DEBUG_MODE,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if search is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isSearchEnabled($storeId = null): bool
    {
        return $this->isEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_SEARCH_ENABLED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if autocomplete is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isAutocompleteEnabled($storeId = null): bool
    {
        return $this->isSearchEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_AUTOCOMPLETE_ENABLED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if recommendations are enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isRecommendationsEnabled($storeId = null): bool
    {
        return $this->isEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_RECOMMENDATIONS_ENABLED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Check if analytics are enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isAnalyticsEnabled($storeId = null): bool
    {
        return $this->isEnabled($storeId) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_ANALYTICS_ENABLED,
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Get search service port
     *
     * @return int
     */
    public function getSearchServicePort(): int
    {
        return $this->servicePorts['search'];
    }

    /**
     * Get recommendation service port
     *
     * @return int
     */
    public function getRecommendationServicePort(): int
    {
        return $this->servicePorts['recommendation'];
    }

    /**
     * Get analytics service port
     *
     * @return int
     */
    public function getAnalyticsServicePort(): int
    {
        return $this->servicePorts['analytics'];
    }

    /**
     * Get shopping assistant port
     *
     * @return int
     */
    public function getShoppingAssistantPort(): int
    {
        return $this->servicePorts['shopping_assistant'];
    }

    /**
     * Get listing optimizer port
     *
     * @return int
     */
    public function getListingOptimizerPort(): int
    {
        return $this->servicePorts['listing_optimizer'];
    }

    /**
     * Get full API URL for a service
     *
     * @param string $service
     * @param string $endpoint
     * @param int|null $storeId
     * @return string
     */
    public function getServiceUrl(string $service, string $endpoint = '', $storeId = null): string
    {
        $baseUrl = $this->getApiBaseUrl($storeId);
        $port = $this->servicePorts[$service] ?? 7001;
        
        return $baseUrl . ':' . $port . $endpoint;
    }
}