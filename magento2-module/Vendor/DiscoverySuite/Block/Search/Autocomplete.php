<?php
/**
 * DiscoverySuite Search Autocomplete Block
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Block\Search;

use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;
use Magento\Framework\Serialize\Serializer\Json;

class Autocomplete extends Template
{
    /**
     * @var ScopeConfigInterface
     */
    private $scopeConfig;

    /**
     * @var Json
     */
    private $jsonSerializer;

    /**
     * Configuration paths
     */
    const XML_PATH_SEARCH_ENABLED = 'discovery_suite/search/enabled';
    const XML_PATH_AUTOCOMPLETE_ENABLED = 'discovery_suite/search/autocomplete_enabled';
    const XML_PATH_AUTOCOMPLETE_MIN_CHARS = 'discovery_suite/search/autocomplete_min_chars';
    const XML_PATH_AUTOCOMPLETE_MAX_RESULTS = 'discovery_suite/search/autocomplete_max_results';

    /**
     * @param Context $context
     * @param ScopeConfigInterface $scopeConfig
     * @param Json $jsonSerializer
     * @param array $data
     */
    public function __construct(
        Context $context,
        ScopeConfigInterface $scopeConfig,
        Json $jsonSerializer,
        array $data = []
    ) {
        $this->scopeConfig = $scopeConfig;
        $this->jsonSerializer = $jsonSerializer;
        parent::__construct($context, $data);
    }

    /**
     * Check if autocomplete is enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_SEARCH_ENABLED,
            ScopeInterface::SCOPE_STORE
        ) && $this->scopeConfig->isSetFlag(
            self::XML_PATH_AUTOCOMPLETE_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Get autocomplete configuration
     *
     * @return string JSON encoded configuration
     */
    public function getAutocompleteConfig(): string
    {
        $config = [
            'enabled' => $this->isEnabled(),
            'minChars' => $this->getMinChars(),
            'maxResults' => $this->getMaxResults(),
            'url' => $this->getAutocompleteUrl(),
            'delay' => 300, // 300ms delay
            'showProducts' => true,
            'showCategories' => true,
            'showSuggestions' => true
        ];

        return $this->jsonSerializer->serialize($config);
    }

    /**
     * Get minimum characters for autocomplete
     *
     * @return int
     */
    public function getMinChars(): int
    {
        return (int) $this->scopeConfig->getValue(
            self::XML_PATH_AUTOCOMPLETE_MIN_CHARS,
            ScopeInterface::SCOPE_STORE
        ) ?: 2;
    }

    /**
     * Get maximum autocomplete results
     *
     * @return int
     */
    public function getMaxResults(): int
    {
        return (int) $this->scopeConfig->getValue(
            self::XML_PATH_AUTOCOMPLETE_MAX_RESULTS,
            ScopeInterface::SCOPE_STORE
        ) ?: 10;
    }

    /**
     * Get autocomplete AJAX URL
     *
     * @return string
     */
    public function getAutocompleteUrl(): string
    {
        return $this->getUrl('discoverysuite/search/autocomplete');
    }

    /**
     * Get search URL
     *
     * @return string
     */
    public function getSearchUrl(): string
    {
        return $this->getUrl('catalogsearch/result');
    }

    /**
     * Get current search query
     *
     * @return string
     */
    public function getCurrentQuery(): string
    {
        return $this->_request->getParam('q', '');
    }

    /**
     * Get search input placeholder
     *
     * @return string
     */
    public function getSearchPlaceholder(): string
    {
        return __('Search products with AI assistance...');
    }
}