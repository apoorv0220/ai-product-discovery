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
    
    const XML_PATH_SEARCH_ENABLED = 'discovery_suite_config/search/enabled';
    const XML_PATH_AUTOCOMPLETE_ENABLED = 'discovery_suite_config/search/autocomplete_enabled';
    
    const XML_PATH_RECOMMENDATIONS_ENABLED = 'discovery_suite_config/recommendations/enabled';
    
    const XML_PATH_ANALYTICS_ENABLED = 'discovery_suite_config/analytics/enabled';

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