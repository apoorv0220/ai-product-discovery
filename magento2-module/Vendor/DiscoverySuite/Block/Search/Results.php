<?php
/**
 * DiscoverySuite Search Results Block
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
use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Psr\Log\LoggerInterface;

class Results extends Template
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
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @var array|null
     */
    private $searchResults;

    /**
     * @param Context $context
     * @param SearchInterface $searchService
     * @param Data $helper
     * @param LoggerInterface $logger
     * @param array $data
     */
    public function __construct(
        Context $context,
        SearchInterface $searchService,
        Data $helper,
        LoggerInterface $logger,
        array $data = []
    ) {
        $this->searchService = $searchService;
        $this->helper = $helper;
        $this->logger = $logger;
        parent::__construct($context, $data);
    }

    /**
     * Get search results
     *
     * @return array
     */
    public function getSearchResults(): array
    {
        if ($this->searchResults === null) {
            $this->searchResults = $this->loadSearchResults();
        }
        
        return $this->searchResults;
    }

    /**
     * Load search results from API
     *
     * @return array
     */
    private function loadSearchResults(): array
    {
        try {
            $query = $this->getRequest()->getParam('q', '');
            
            if (empty($query)) {
                return [];
            }

            $limit = (int) $this->getRequest()->getParam('limit', 20);
            $offset = (int) $this->getRequest()->getParam('offset', 0);
            
            return $this->searchService->search($query, $limit, $offset, []);
            
        } catch (\Exception $e) {
            $this->logger->error('Search results block error: ' . $e->getMessage());
            return [];
        }
    }

    /**
     * Get search query
     *
     * @return string
     */
    public function getSearchQuery(): string
    {
        return (string) $this->getRequest()->getParam('q', '');
    }

    /**
     * Check if AI search is enabled
     *
     * @return bool
     */
    public function isAiSearchEnabled(): bool
    {
        return $this->helper->isSearchEnabled();
    }

    /**
     * Get API configuration
     *
     * @return array
     */
    public function getApiConfig(): array
    {
        return [
            'search_endpoint' => $this->helper->getServiceUrl('search', '/api/v1/search/'),
            'autocomplete_endpoint' => $this->helper->getServiceUrl('search', '/api/v1/autocomplete/'),
            'enabled' => $this->isAiSearchEnabled()
        ];
    }

    /**
     * Get JSON encoded API config for JavaScript
     *
     * @return string
     */
    public function getApiConfigJson(): string
    {
        return json_encode($this->getApiConfig());
    }

    /**
     * Check if there are search results
     *
     * @return bool
     */
    public function hasResults(): bool
    {
        $results = $this->getSearchResults();
        return !empty($results['results']);
    }

    /**
     * Get total results count
     *
     * @return int
     */
    public function getTotalResults(): int
    {
        $results = $this->getSearchResults();
        return (int) ($results['total'] ?? 0);
    }

    /**
     * Get search response time
     *
     * @return float
     */
    public function getResponseTime()
    {
        $results = $this->getSearchResults();
        return (float) ($results['took'] ?? 0);
    }
    
    /**
     * Get current user ID for personalized search
     *
     * @return string
     */
    private function getUserId()
    {
        $customerSession = $this->_objectManager->get(\Magento\Customer\Model\Session::class);
        
        if ($customerSession->isLoggedIn()) {
            return 'customer_' . $customerSession->getCustomerId();
        }
        
        $sessionManager = $this->_objectManager->get(\Magento\Framework\Session\SessionManagerInterface::class);
        return 'guest_' . $sessionManager->getSessionId();
    }
}
