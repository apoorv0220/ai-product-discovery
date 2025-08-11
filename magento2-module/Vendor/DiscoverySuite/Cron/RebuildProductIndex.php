<?php
/**
 * DiscoverySuite Rebuild Product Index Cron
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Cron;

use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Catalog\Api\ProductRepositoryInterface;
use Magento\Framework\Api\SearchCriteriaBuilder;
use Magento\Store\Model\StoreManagerInterface;
use Psr\Log\LoggerInterface;

class RebuildProductIndex
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
     * @var ProductRepositoryInterface
     */
    private $productRepository;

    /**
     * @var SearchCriteriaBuilder
     */
    private $searchCriteriaBuilder;

    /**
     * @var StoreManagerInterface
     */
    private $storeManager;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param SearchInterface $searchService
     * @param Data $helper
     * @param ProductRepositoryInterface $productRepository
     * @param SearchCriteriaBuilder $searchCriteriaBuilder
     * @param StoreManagerInterface $storeManager
     * @param LoggerInterface $logger
     */
    public function __construct(
        SearchInterface $searchService,
        Data $helper,
        ProductRepositoryInterface $productRepository,
        SearchCriteriaBuilder $searchCriteriaBuilder,
        StoreManagerInterface $storeManager,
        LoggerInterface $logger
    ) {
        $this->searchService = $searchService;
        $this->helper = $helper;
        $this->productRepository = $productRepository;
        $this->searchCriteriaBuilder = $searchCriteriaBuilder;
        $this->storeManager = $storeManager;
        $this->logger = $logger;
    }

    /**
     * Execute product index rebuild
     *
     * @return void
     */
    public function execute(): void
    {
        if (!$this->helper->isSearchEnabled()) {
            return;
        }

        $this->logger->info('Starting product index rebuild');

        try {
            foreach ($this->storeManager->getStores() as $store) {
                $this->rebuildStoreIndex((int) $store->getId());
            }

            $this->logger->info('Product index rebuild completed successfully');

        } catch (\Exception $e) {
            $this->logger->error('Product index rebuild failed', [
                'error' => $e->getMessage()
            ]);
        }
    }

    /**
     * Rebuild index for specific store
     *
     * @param int $storeId
     * @return void
     */
    private function rebuildStoreIndex(int $storeId): void
    {
        try {
            $batchSize = 100;
            $currentPage = 1;
            $totalIndexed = 0;

            do {
                $searchCriteria = $this->searchCriteriaBuilder
                    ->addFilter('status', 1) // Enabled products only
                    ->setPageSize($batchSize)
                    ->setCurrentPage($currentPage)
                    ->create();

                $products = $this->productRepository->getList($searchCriteria);
                $productData = [];

                foreach ($products->getItems() as $product) {
                    $productData[] = $this->formatProductForIndex($product, $storeId);
                }

                if (!empty($productData)) {
                    $this->searchService->indexProducts($productData);
                    $totalIndexed += count($productData);
                }

                $currentPage++;
            } while ($currentPage <= $products->getTotalCount() / $batchSize + 1);

            $this->logger->info('Store index rebuilt', [
                'store_id' => $storeId,
                'total_indexed' => $totalIndexed
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Store index rebuild failed', [
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);
        }
    }

    /**
     * Format product data for indexing
     *
     * @param \Magento\Catalog\Api\Data\ProductInterface $product
     * @param int $storeId
     * @return array
     */
    private function formatProductForIndex($product, int $storeId): array
    {
        return [
            'id' => $product->getId(),
            'sku' => $product->getSku(),
            'name' => $product->getName(),
            'description' => $product->getDescription(),
            'short_description' => $product->getShortDescription(),
            'price' => $product->getPrice(),
            'special_price' => $product->getSpecialPrice(),
            'category_ids' => $product->getCategoryIds(),
            'status' => $product->getStatus(),
            'visibility' => $product->getVisibility(),
            'type_id' => $product->getTypeId(),
            'store_id' => $storeId,
            'updated_at' => date('c')
        ];
    }
}