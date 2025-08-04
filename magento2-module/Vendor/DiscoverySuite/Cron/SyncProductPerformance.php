<?php
/**
 * DiscoverySuite Product Performance Sync Cron
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Cron;

use Vendor\DiscoverySuite\Model\Listing\ListingOptimizer;
use Magento\Catalog\Api\ProductRepositoryInterface;
use Magento\Framework\Api\SearchCriteriaBuilder;
use Magento\Sales\Model\ResourceModel\Order\Item\CollectionFactory as OrderItemCollectionFactory;
use Magento\Store\Model\StoreManagerInterface;
use Magento\Framework\Stdlib\DateTime\DateTime;
use Psr\Log\LoggerInterface;

class SyncProductPerformance
{
    /**
     * @var ListingOptimizer
     */
    private $listingOptimizer;

    /**
     * @var ProductRepositoryInterface
     */
    private $productRepository;

    /**
     * @var SearchCriteriaBuilder
     */
    private $searchCriteriaBuilder;

    /**
     * @var OrderItemCollectionFactory
     */
    private $orderItemCollectionFactory;

    /**
     * @var StoreManagerInterface
     */
    private $storeManager;

    /**
     * @var DateTime
     */
    private $dateTime;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param ListingOptimizer $listingOptimizer
     * @param ProductRepositoryInterface $productRepository
     * @param SearchCriteriaBuilder $searchCriteriaBuilder
     * @param OrderItemCollectionFactory $orderItemCollectionFactory
     * @param StoreManagerInterface $storeManager
     * @param DateTime $dateTime
     * @param LoggerInterface $logger
     */
    public function __construct(
        ListingOptimizer $listingOptimizer,
        ProductRepositoryInterface $productRepository,
        SearchCriteriaBuilder $searchCriteriaBuilder,
        OrderItemCollectionFactory $orderItemCollectionFactory,
        StoreManagerInterface $storeManager,
        DateTime $dateTime,
        LoggerInterface $logger
    ) {
        $this->listingOptimizer = $listingOptimizer;
        $this->productRepository = $productRepository;
        $this->searchCriteriaBuilder = $searchCriteriaBuilder;
        $this->orderItemCollectionFactory = $orderItemCollectionFactory;
        $this->storeManager = $storeManager;
        $this->dateTime = $dateTime;
        $this->logger = $logger;
    }

    /**
     * Execute cron job to sync product performance data
     *
     * @return void
     */
    public function execute(): void
    {
        if (!$this->listingOptimizer->isEnabled()) {
            return;
        }

        $this->logger->info('Starting product performance sync');

        try {
            foreach ($this->storeManager->getStores() as $store) {
                $this->syncStorePerformance((int) $store->getId());
            }

            $this->logger->info('Product performance sync completed successfully');

        } catch (\Exception $e) {
            $this->logger->error('Product performance sync failed', [
                'error' => $e->getMessage()
            ]);
        }
    }

    /**
     * Sync performance data for specific store
     *
     * @param int $storeId
     * @return void
     */
    private function syncStorePerformance(int $storeId): void
    {
        $this->logger->info('Syncing performance data for store', ['store_id' => $storeId]);

        try {
            // Get all active products
            $searchCriteria = $this->searchCriteriaBuilder
                ->addFilter('status', 1)
                ->addFilter('store_id', $storeId)
                ->create();

            $products = $this->productRepository->getList($searchCriteria);
            $productIds = [];

            foreach ($products->getItems() as $product) {
                $productIds[] = (int) $product->getId();
            }

            if (empty($productIds)) {
                $this->logger->info('No products found for store', ['store_id' => $storeId]);
                return;
            }

            // Calculate performance metrics
            $performanceData = $this->calculatePerformanceMetrics($productIds, $storeId);

            // Sync with AI service
            $success = $this->listingOptimizer->syncProductPerformance($productIds, $storeId);

            if ($success) {
                $this->logger->info('Successfully synced performance data', [
                    'store_id' => $storeId,
                    'product_count' => count($productIds)
                ]);
            } else {
                $this->logger->warning('Failed to sync performance data', [
                    'store_id' => $storeId,
                    'product_count' => count($productIds)
                ]);
            }

        } catch (\Exception $e) {
            $this->logger->error('Store performance sync failed', [
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);
        }
    }

    /**
     * Calculate performance metrics for products
     *
     * @param array $productIds
     * @param int $storeId
     * @return array
     */
    private function calculatePerformanceMetrics(array $productIds, int $storeId): array
    {
        $metrics = [];

        try {
            // Calculate sales performance for the last 30 days
            $fromDate = $this->dateTime->gmtDate('Y-m-d H:i:s', strtotime('-30 days'));
            $toDate = $this->dateTime->gmtDate('Y-m-d H:i:s');

            $orderItemCollection = $this->orderItemCollectionFactory->create();
            $orderItemCollection->addFieldToSelect(['product_id', 'qty_ordered', 'row_total'])
                ->addFieldToFilter('product_id', ['in' => $productIds])
                ->addFieldToFilter('created_at', ['from' => $fromDate, 'to' => $toDate]);

            // Join with order table to filter by store
            $orderItemCollection->getSelect()
                ->join(
                    ['order' => $orderItemCollection->getTable('sales_order')],
                    'main_table.order_id = order.entity_id',
                    []
                )
                ->where('order.store_id = ?', $storeId);

            foreach ($orderItemCollection as $item) {
                $productId = (int) $item->getProductId();
                
                if (!isset($metrics[$productId])) {
                    $metrics[$productId] = [
                        'product_id' => $productId,
                        'sales_count' => 0,
                        'revenue' => 0,
                        'view_count' => 0, // This would come from analytics service
                        'conversion_rate' => 0,
                        'popularity_score' => 0
                    ];
                }

                $metrics[$productId]['sales_count'] += (int) $item->getQtyOrdered();
                $metrics[$productId]['revenue'] += (float) $item->getRowTotal();
            }

            // Calculate derived metrics
            foreach ($metrics as $productId => &$metric) {
                // Simple popularity score based on sales
                $metric['popularity_score'] = ($metric['sales_count'] * 0.7) + ($metric['revenue'] * 0.3);
                
                // Conversion rate (would be more accurate with view data from analytics)
                if ($metric['view_count'] > 0) {
                    $metric['conversion_rate'] = $metric['sales_count'] / $metric['view_count'];
                }
            }

        } catch (\Exception $e) {
            $this->logger->error('Performance metrics calculation failed', [
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);
        }

        return $metrics;
    }

    /**
     * Sync trending products
     *
     * @return void
     */
    public function syncTrendingProducts(): void
    {
        if (!$this->listingOptimizer->isEnabled()) {
            return;
        }

        $this->logger->info('Starting trending products sync');

        try {
            // Get top selling products in the last 7 days
            $fromDate = $this->dateTime->gmtDate('Y-m-d H:i:s', strtotime('-7 days'));
            
            foreach ($this->storeManager->getStores() as $store) {
                $storeId = (int) $store->getId();
                
                $orderItemCollection = $this->orderItemCollectionFactory->create();
                $orderItemCollection->addFieldToSelect(['product_id', 'qty_ordered'])
                    ->addFieldToFilter('created_at', ['from' => $fromDate]);

                $orderItemCollection->getSelect()
                    ->join(
                        ['order' => $orderItemCollection->getTable('sales_order')],
                        'main_table.order_id = order.entity_id',
                        []
                    )
                    ->where('order.store_id = ?', $storeId)
                    ->group('main_table.product_id')
                    ->order('SUM(main_table.qty_ordered) DESC')
                    ->limit(100);

                $trendingProductIds = [];
                foreach ($orderItemCollection as $item) {
                    $trendingProductIds[] = (int) $item->getProductId();
                }

                if (!empty($trendingProductIds)) {
                    // This would sync trending data with the AI service
                    $this->logger->info('Found trending products for store', [
                        'store_id' => $storeId,
                        'trending_count' => count($trendingProductIds)
                    ]);
                }
            }

        } catch (\Exception $e) {
            $this->logger->error('Trending products sync failed', [
                'error' => $e->getMessage()
            ]);
        }
    }
}