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

use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Framework\Json\Helper\Data as JsonHelper;

class Autocomplete extends Template
{
    /**
     * @var SearchInterface
     */
    private $searchService;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var JsonHelper
     */
    private $jsonHelper;

    /**
     * Constructor
     *
     * @param Context $context
     * @param SearchInterface $searchService
     * @param Data $helper
     * @param JsonHelper $jsonHelper
     * @param array $data
     */
    public function __construct(
        Context $context,
        SearchInterface $searchService,
        Data $helper,
        JsonHelper $jsonHelper,
        array $data = []
    ) {
        $this->searchService = $searchService;
        $this->helper = $helper;
        $this->jsonHelper = $jsonHelper;
        parent::__construct($context, $data);
    }

    /**
     * Check if autocomplete is enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->helper->isAutocompleteEnabled();
    }

    /**
     * Get autocomplete configuration as JSON
     *
     * @return string
     */
    public function getConfigJson(): string
    {
        $config = [
            'enabled' => $this->isEnabled(),
            'minSearchLength' => 2,
            'delay' => 300,
            'maxSuggestions' => 10,
            'endpoint' => $this->getUrl('discovery/search/autocomplete'),
            'showImages' => true,
            'showPrices' => true,
            'showCategories' => true
        ];

        return $this->jsonHelper->jsonEncode($config);
    }

    /**
     * Get autocomplete suggestions for query
     *
     * @param string $query
     * @param int $limit
     * @return array
     */
    public function getSuggestions(string $query, int $limit = 10): array
    {
        if (!$this->isEnabled()) {
            return [];
        }

        try {
            return $this->searchService->autocomplete($query, $limit);
        } catch (\Exception $e) {
            $this->_logger->error('Autocomplete suggestions failed', [
                'query' => $query,
                'error' => $e->getMessage()
            ]);
            return [];
        }
    }

    /**
     * Get cache key info
     *
     * @return array
     */
    public function getCacheKeyInfo()
    {
        return [
            'DISCOVERY_AUTOCOMPLETE',
            $this->_storeManager->getStore()->getId(),
            $this->getTemplateFile()
        ];
    }
}