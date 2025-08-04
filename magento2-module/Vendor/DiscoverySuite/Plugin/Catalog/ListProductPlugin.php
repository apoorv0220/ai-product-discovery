<?php
/**
 * DiscoverySuite Catalog List Product Plugin
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Plugin\Catalog;

use Magento\Catalog\Block\Product\ListProduct;
use Vendor\DiscoverySuite\Model\Listing\ListingOptimizer;
use Magento\Framework\Registry;
use Psr\Log\LoggerInterface;

class ListProductPlugin
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
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param ListingOptimizer $listingOptimizer
     * @param Registry $registry
     * @param LoggerInterface $logger
     */
    public function __construct(
        ListingOptimizer $listingOptimizer,
        Registry $registry,
        LoggerInterface $logger
    ) {
        $this->listingOptimizer = $listingOptimizer;
        $this->registry = $registry;
        $this->logger = $logger;
    }

    /**
     * Optimize product collection before rendering
     *
     * @param ListProduct $subject
     * @param callable $proceed
     * @return \Magento\Catalog\Model\ResourceModel\Product\Collection
     */
    public function aroundGetLoadedProductCollection(ListProduct $subject, callable $proceed)
    {
        $collection = $proceed();

        if (!$this->listingOptimizer->isEnabled()) {
            return $collection;
        }

        try {
            // Get current category from registry
            $currentCategory = $this->registry->registry('current_category');
            
            $context = [
                'page_type' => 'category',
                'category_id' => $currentCategory ? $currentCategory->getId() : null,
                'store_id' => $subject->getStoreId(),
                'page_number' => $subject->getRequest()->getParam('p', 1),
                'sort_order' => $subject->getRequest()->getParam('product_list_order'),
                'applied_filters' => $this->getAppliedFilters($subject)
            ];

            // Apply AI optimization to the collection
            $optimizedCollection = $this->listingOptimizer->optimizeCollection($collection, $context);

            return $optimizedCollection;

        } catch (\Exception $e) {
            $this->logger->error('List product plugin error', [
                'error' => $e->getMessage(),
                'category_id' => $currentCategory ? $currentCategory->getId() : null
            ]);

            return $collection;
        }
    }

    /**
     * Get applied filters from request
     *
     * @param ListProduct $subject
     * @return array
     */
    private function getAppliedFilters(ListProduct $subject): array
    {
        $request = $subject->getRequest();
        $filters = [];

        // Get all request parameters that might be filters
        foreach ($request->getParams() as $key => $value) {
            // Skip standard pagination/sorting parameters
            if (in_array($key, ['p', 'product_list_order', 'product_list_dir', 'product_list_limit'])) {
                continue;
            }

            // Include filter parameters
            if (!empty($value) && $key !== 'id') {
                $filters[$key] = $value;
            }
        }

        return $filters;
    }
}