<?php
/**
 * DiscoverySuite Dynamic Filters Block
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Block\Listing;

use Vendor\DiscoverySuite\Model\Listing\ListingOptimizer;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Framework\Json\Helper\Data as JsonHelper;
use Magento\Framework\Registry;
use Magento\Catalog\Model\Layer\Resolver;
use Magento\Customer\Model\Session as CustomerSession;

class DynamicFilters extends Template
{
    /**
     * @var ListingOptimizer
     */
    private $listingOptimizer;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var JsonHelper
     */
    private $jsonHelper;

    /**
     * @var Registry
     */
    private $registry;

    /**
     * @var Resolver
     */
    private $layerResolver;

    /**
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * Constructor
     *
     * @param Context $context
     * @param ListingOptimizer $listingOptimizer
     * @param Data $helper
     * @param JsonHelper $jsonHelper
     * @param Registry $registry
     * @param Resolver $layerResolver
     * @param CustomerSession $customerSession
     * @param array $data
     */
    public function __construct(
        Context $context,
        ListingOptimizer $listingOptimizer,
        Data $helper,
        JsonHelper $jsonHelper,
        Registry $registry,
        Resolver $layerResolver,
        CustomerSession $customerSession,
        array $data = []
    ) {
        $this->listingOptimizer = $listingOptimizer;
        $this->helper = $helper;
        $this->jsonHelper = $jsonHelper;
        $this->registry = $registry;
        $this->layerResolver = $layerResolver;
        $this->customerSession = $customerSession;
        parent::__construct($context, $data);
    }

    /**
     * Check if dynamic filters are enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->helper->isEnabled() && $this->listingOptimizer->isEnabled();
    }

    /**
     * Get dynamic filters for current category
     *
     * @return array
     */
    public function getDynamicFilters(): array
    {
        if (!$this->isEnabled()) {
            return [];
        }

        $currentCategory = $this->registry->registry('current_category');
        if (!$currentCategory) {
            return [];
        }

        try {
            $context = $this->getFilterContext();
            return $this->listingOptimizer->getDynamicFilters(
                (int) $currentCategory->getId(),
                $context
            );

        } catch (\Exception $e) {
            $this->_logger->error('Dynamic filters loading failed', [
                'category_id' => $currentCategory->getId(),
                'error' => $e->getMessage()
            ]);
            return [];
        }
    }

    /**
     * Get filters configuration as JSON
     *
     * @return string
     */
    public function getConfigJson(): string
    {
        $config = [
            'enabled' => $this->isEnabled(),
            'filters' => $this->getDynamicFilters(),
            'ajaxUrl' => $this->getUrl('discovery/listing/filters'),
            'autoApply' => true,
            'showCounts' => true
        ];

        return $this->jsonHelper->jsonEncode($config);
    }

    /**
     * Get filter context information
     *
     * @return array
     */
    private function getFilterContext(): array
    {
        $context = [];

        // Add current applied filters
        try {
            $layer = $this->layerResolver->get();
            $appliedFilters = [];
            
            foreach ($layer->getState()->getFilters() as $filter) {
                $appliedFilters[$filter->getFilter()->getRequestVar()] = $filter->getValue();
            }
            
            $context['applied_filters'] = $appliedFilters;
        } catch (\Exception $e) {
            // Ignore if layer is not available
        }

        // Add search query if in search context
        $searchQuery = $this->getRequest()->getParam('q');
        if ($searchQuery) {
            $context['search_query'] = $searchQuery;
        }

        // Add user preferences
        $context['user_id'] = $this->getUserId();
        $context['store_id'] = $this->_storeManager->getStore()->getId();

        return $context;
    }

    /**
     * Get user ID for personalization
     *
     * @return string
     */
    private function getUserId(): string
    {
        if ($this->customerSession->isLoggedIn()) {
            return 'customer_' . $this->customerSession->getCustomerId();
        }

        return 'guest_' . $this->customerSession->getSessionId();
    }

    /**
     * Get cache key info
     *
     * @return array
     */
    public function getCacheKeyInfo()
    {
        $currentCategory = $this->registry->registry('current_category');
        
        return [
            'DISCOVERY_DYNAMIC_FILTERS',
            $this->_storeManager->getStore()->getId(),
            $currentCategory ? $currentCategory->getId() : 'no_category',
            $this->getUserId(),
            $this->getRequest()->getParam('q', '')
        ];
    }
}