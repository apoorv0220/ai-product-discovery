<?php
/**
 * DiscoverySuite List Product Plugin
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Plugin\Catalog;

use Vendor\DiscoverySuite\Model\Listing\ListingOptimizer;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Catalog\Block\Product\ListProduct;
use Magento\Catalog\Model\ResourceModel\Product\Collection;
use Magento\Framework\Registry;
use Psr\Log\LoggerInterface;

class ListProductPlugin
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
     * @var Registry
     */
    private $registry;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param ListingOptimizer $listingOptimizer
     * @param Data $helper
     * @param Registry $registry
     * @param LoggerInterface $logger
     */
    public function __construct(
        ListingOptimizer $listingOptimizer,
        Data $helper,
        Registry $registry,
        LoggerInterface $logger
    ) {
        $this->listingOptimizer = $listingOptimizer;
        $this->helper = $helper;
        $this->registry = $registry;
        $this->logger = $logger;
    }

    /**
     * Around method for getLoadedProductCollection to optimize product order
     *
     * @param ListProduct $subject
     * @param callable $proceed
     * @return Collection
     */
    public function aroundGetLoadedProductCollection(ListProduct $subject, callable $proceed)
    {
        $collection = $proceed();

        if (!$this->helper->isEnabled() || !$this->listingOptimizer->isEnabled()) {
            return $collection;
        }

        try {
            // Get current category
            $currentCategory = $this->registry->registry('current_category');
            $context = 'category';
            $categoryId = null;

            if ($currentCategory) {
                $categoryId = $currentCategory->getId();
            } else {
                $context = 'search';
            }

            // Get product IDs from collection
            $productIds = [];
            foreach ($collection as $product) {
                $productIds[] = (int) $product->getId();
            }

            if (!empty($productIds)) {
                // Get optimized order from AI service
                $optimizedOrder = $this->listingOptimizer->optimizeListingOrder(
                    $productIds,
                    $context,
                    ['category_id' => $categoryId]
                );

                // Apply optimized ordering if different from current
                if ($optimizedOrder !== $productIds && count($optimizedOrder) > 1) {
                    $orderField = new \Zend_Db_Expr('FIELD(e.entity_id,' . implode(',', $optimizedOrder) . ')');
                    $collection->getSelect()->order($orderField);

                    $this->logger->info('AI listing optimization applied', [
                        'context' => $context,
                        'category_id' => $categoryId,
                        'original_count' => count($productIds),
                        'optimized_count' => count($optimizedOrder)
                    ]);
                }
            }

        } catch (\Exception $e) {
            $this->logger->error('Listing optimization failed', [
                'error' => $e->getMessage()
            ]);
        }

        return $collection;
    }

    /**
     * After method for getMode to potentially inject AI insights
     *
     * @param ListProduct $subject
     * @param string $result
     * @return string
     */
    public function afterGetMode(ListProduct $subject, $result)
    {
        // Could be used to inject AI-driven view mode recommendations
        return $result;
    }
}