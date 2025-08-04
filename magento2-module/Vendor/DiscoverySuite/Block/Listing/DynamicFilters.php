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

use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Vendor\DiscoverySuite\Model\Listing\ListingOptimizer;
use Magento\Framework\Registry;
use Magento\Framework\Serialize\Serializer\Json;

class DynamicFilters extends Template
{
    /**
     * @var ListingOptimizer
     */
    private $listingOptimizer;

    /**
     * @var Registry
     */
    private $registry;

    /**
     * @var Json
     */
    private $jsonSerializer;

    /**
     * @param Context $context
     * @param ListingOptimizer $listingOptimizer
     * @param Registry $registry
     * @param Json $jsonSerializer
     * @param array $data
     */
    public function __construct(
        Context $context,
        ListingOptimizer $listingOptimizer,
        Registry $registry,
        Json $jsonSerializer,
        array $data = []
    ) {
        $this->listingOptimizer = $listingOptimizer;
        $this->registry = $registry;
        $this->jsonSerializer = $jsonSerializer;
        parent::__construct($context, $data);
    }

    /**
     * Check if dynamic filters are enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->listingOptimizer->isDynamicFiltersEnabled();
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
        $categoryId = $currentCategory ? $currentCategory->getId() : null;

        try {
            return $this->listingOptimizer->getDynamicFilters($categoryId);
        } catch (\Exception $e) {
            $this->_logger->error('Failed to get dynamic filters', [
                'category_id' => $categoryId,
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
    public function getFiltersConfig(): string
    {
        $filters = $this->getDynamicFilters();
        
        $config = [
            'filters' => $filters,
            'enabled' => $this->isEnabled(),
            'category_id' => $this->getCurrentCategoryId(),
            'ajax_url' => $this->getUrl('discoverysuite/listing/filter')
        ];

        return $this->jsonSerializer->serialize($config);
    }

    /**
     * Get current category ID
     *
     * @return int|null
     */
    public function getCurrentCategoryId(): ?int
    {
        $currentCategory = $this->registry->registry('current_category');
        return $currentCategory ? (int) $currentCategory->getId() : null;
    }

    /**
     * Check if should show filters
     *
     * @return bool
     */
    public function shouldShow(): bool
    {
        return $this->isEnabled() && !empty($this->getDynamicFilters());
    }

    /**
     * Get applied filters from request
     *
     * @return array
     */
    public function getAppliedFilters(): array
    {
        $applied = [];
        $request = $this->getRequest();

        foreach ($this->getDynamicFilters() as $filter) {
            $code = $filter['code'] ?? '';
            $value = $request->getParam($code);

            if (!empty($value)) {
                $applied[$code] = $value;
            }
        }

        return $applied;
    }

    /**
     * Get clear filter URL
     *
     * @param string $filterCode
     * @return string
     */
    public function getClearFilterUrl(string $filterCode): string
    {
        $params = $this->getRequest()->getParams();
        unset($params[$filterCode]);

        return $this->getUrl('*/*/*', ['_current' => false, '_use_rewrite' => true, '_query' => $params]);
    }

    /**
     * Get filter value URL
     *
     * @param string $filterCode
     * @param mixed $value
     * @return string
     */
    public function getFilterUrl(string $filterCode, $value): string
    {
        $params = $this->getRequest()->getParams();
        $params[$filterCode] = $value;

        return $this->getUrl('*/*/*', ['_current' => false, '_use_rewrite' => true, '_query' => $params]);
    }
}