<?php
/**
 * DiscoverySuite Sync Catalog Console Command
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Console\Command;

use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Helper\ProgressBar;
use Vendor\DiscoverySuite\Api\SearchInterface;
use Magento\Catalog\Api\ProductRepositoryInterface;
use Magento\Framework\Api\SearchCriteriaBuilder;
use Magento\Store\Model\StoreManagerInterface;

class SyncCatalog extends Command
{
    /**
     * @var SearchInterface
     */
    private $searchService;

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
     * @param SearchInterface $searchService
     * @param ProductRepositoryInterface $productRepository
     * @param SearchCriteriaBuilder $searchCriteriaBuilder
     * @param StoreManagerInterface $storeManager
     */
    public function __construct(
        SearchInterface $searchService,
        ProductRepositoryInterface $productRepository,
        SearchCriteriaBuilder $searchCriteriaBuilder,
        StoreManagerInterface $storeManager
    ) {
        $this->searchService = $searchService;
        $this->productRepository = $productRepository;
        $this->searchCriteriaBuilder = $searchCriteriaBuilder;
        $this->storeManager = $storeManager;
        parent::__construct();
    }

    /**
     * Configure command
     */
    protected function configure(): void
    {
        $this->setName('discovery:catalog:sync')
            ->setDescription('Sync catalog with AI Discovery Suite')
            ->addOption(
                'store-id',
                's',
                InputOption::VALUE_OPTIONAL,
                'Store ID to sync (default: all stores)'
            )
            ->addOption(
                'batch-size',
                'b',
                InputOption::VALUE_OPTIONAL,
                'Batch size for product sync',
                100
            )
            ->addOption(
                'product-id',
                'p',
                InputOption::VALUE_OPTIONAL,
                'Specific product ID to sync'
            );
    }

    /**
     * Execute command
     *
     * @param InputInterface $input
     * @param OutputInterface $output
     * @return int
     */
    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $output->writeln('<info>Starting catalog sync with AI Discovery Suite...</info>');

        $storeId = $input->getOption('store-id');
        $batchSize = (int) $input->getOption('batch-size');
        $productId = $input->getOption('product-id');

        try {
            if ($productId) {
                return $this->syncSingleProduct((int) $productId, $storeId, $output);
            } else {
                return $this->syncAllProducts($storeId, $batchSize, $output);
            }
        } catch (\Exception $e) {
            $output->writeln('<error>Error during sync: ' . $e->getMessage() . '</error>');
            return Command::FAILURE;
        }
    }

    /**
     * Sync single product
     *
     * @param int $productId
     * @param string|null $storeId
     * @param OutputInterface $output
     * @return int
     */
    private function syncSingleProduct(int $productId, ?string $storeId, OutputInterface $output): int
    {
        $output->writeln("<info>Syncing product ID: {$productId}</info>");

        $success = $this->searchService->indexProduct($productId, $storeId ? (int) $storeId : null);

        if ($success) {
            $output->writeln('<info>Product synced successfully!</info>');
            return Command::SUCCESS;
        } else {
            $output->writeln('<error>Failed to sync product</error>');
            return Command::FAILURE;
        }
    }

    /**
     * Sync all products
     *
     * @param string|null $storeId
     * @param int $batchSize
     * @param OutputInterface $output
     * @return int
     */
    private function syncAllProducts(?string $storeId, int $batchSize, OutputInterface $output): int
    {
        $stores = $storeId ? [(int) $storeId] : $this->getAllStoreIds();

        foreach ($stores as $currentStoreId) {
            $output->writeln("<info>Syncing store ID: {$currentStoreId}</info>");

            // Get total product count
            $totalProducts = $this->getTotalProductCount($currentStoreId);
            $output->writeln("<info>Total products to sync: {$totalProducts}</info>");

            if ($totalProducts === 0) {
                $output->writeln('<info>No products found for this store</info>');
                continue;
            }

            // Create progress bar
            $progressBar = new ProgressBar($output, $totalProducts);
            $progressBar->start();

            $currentPage = 1;
            $totalPages = ceil($totalProducts / $batchSize);
            $syncedCount = 0;
            $failedCount = 0;

            // Process products in batches
            while ($currentPage <= $totalPages) {
                $products = $this->getProductBatch($currentStoreId, $currentPage, $batchSize);
                
                if (empty($products)) {
                    break;
                }

                $productIds = array_map(function ($product) {
                    return (int) $product->getId();
                }, $products);

                // Bulk index products
                $success = $this->searchService->bulkIndexProducts($productIds, $currentStoreId);

                if ($success) {
                    $syncedCount += count($productIds);
                } else {
                    $failedCount += count($productIds);
                }

                $progressBar->advance(count($productIds));
                $currentPage++;
            }

            $progressBar->finish();
            $output->writeln('');
            $output->writeln("<info>Store {$currentStoreId} sync completed:</info>");
            $output->writeln("<info>  - Synced: {$syncedCount} products</info>");
            $output->writeln("<info>  - Failed: {$failedCount} products</info>");
        }

        $output->writeln('<info>Catalog sync completed!</info>');
        return Command::SUCCESS;
    }

    /**
     * Get all store IDs
     *
     * @return array
     */
    private function getAllStoreIds(): array
    {
        $storeIds = [];
        foreach ($this->storeManager->getStores() as $store) {
            $storeIds[] = (int) $store->getId();
        }
        return $storeIds;
    }

    /**
     * Get total product count for store
     *
     * @param int $storeId
     * @return int
     */
    private function getTotalProductCount(int $storeId): int
    {
        $searchCriteria = $this->searchCriteriaBuilder
            ->addFilter('status', 1) // Only enabled products
            ->create();

        $searchResults = $this->productRepository->getList($searchCriteria);
        return $searchResults->getTotalCount();
    }

    /**
     * Get product batch
     *
     * @param int $storeId
     * @param int $page
     * @param int $pageSize
     * @return array
     */
    private function getProductBatch(int $storeId, int $page, int $pageSize): array
    {
        $searchCriteria = $this->searchCriteriaBuilder
            ->addFilter('status', 1) // Only enabled products
            ->setPageSize($pageSize)
            ->setCurrentPage($page)
            ->create();

        $searchResults = $this->productRepository->getList($searchCriteria);
        return $searchResults->getItems();
    }
}