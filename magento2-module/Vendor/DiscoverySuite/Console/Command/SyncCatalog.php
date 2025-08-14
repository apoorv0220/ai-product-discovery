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

namespace Vendor\DiscoverySuite\Console\Command;

use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Input\InputOption;
use Magento\Framework\App\State;
use Magento\Framework\App\Area;
use Magento\Catalog\Model\ResourceModel\Product\CollectionFactory;
use Magento\Catalog\Model\Product\Visibility;
use Magento\Catalog\Model\Product\Attribute\Source\Status;
use Magento\Store\Model\StoreManagerInterface;
use Magento\Catalog\Helper\Image;
use Magento\Framework\Pricing\Helper\Data as PriceHelper;
use Magento\CatalogInventory\Api\StockRegistryInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;

class SyncCatalog extends Command
{
    const BATCH_SIZE = 'batch-size';
    const STORE_ID = 'store-id';

    /**
     * @var State
     */
    private $appState;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var HttpClient
     */
    private $httpClient;

    /**
     * @var CollectionFactory
     */
    private $productCollectionFactory;

    /**
     * @var StoreManagerInterface
     */
    private $storeManager;

    /**
     * @var Image
     */
    private $imageHelper;

    /**
     * @var PriceHelper
     */
    private $priceHelper;

    /**
     * @var StockRegistryInterface
     */
    private $stockRegistry;

    /**
     * Constructor
     *
     * @param State $appState
     * @param Data $helper
     * @param HttpClient $httpClient
     * @param CollectionFactory $productCollectionFactory
     * @param StoreManagerInterface $storeManager
     * @param Image $imageHelper
     * @param PriceHelper $priceHelper
     * @param StockRegistryInterface $stockRegistry
     * @param string|null $name
     */
    public function __construct(
        State $appState,
        Data $helper,
        HttpClient $httpClient,
        CollectionFactory $productCollectionFactory,
        StoreManagerInterface $storeManager,
        Image $imageHelper,
        PriceHelper $priceHelper,
        StockRegistryInterface $stockRegistry,
        string $name = null
    ) {
        $this->appState = $appState;
        $this->helper = $helper;
        $this->httpClient = $httpClient;
        $this->productCollectionFactory = $productCollectionFactory;
        $this->storeManager = $storeManager;
        $this->imageHelper = $imageHelper;
        $this->priceHelper = $priceHelper;
        $this->stockRegistry = $stockRegistry;
        parent::__construct($name);
    }

    /**
     * Configure command
     */
    protected function configure()
    {
        $this->setName('discovery:sync:catalog')
            ->setDescription('Sync product catalog with AI Discovery Suite')
            ->addOption(
                self::BATCH_SIZE,
                'b',
                InputOption::VALUE_OPTIONAL,
                'Batch size for syncing products',
                100
            )
            ->addOption(
                self::STORE_ID,
                's',
                InputOption::VALUE_OPTIONAL,
                'Store ID to sync',
                1
            );
    }

    /**
     * Execute command
     *
     * @param InputInterface $input
     * @param OutputInterface $output
     * @return int
     */
    protected function execute(InputInterface $input, OutputInterface $output)
    {
        try {
            $this->appState->setAreaCode(Area::AREA_ADMINHTML);
            
            $batchSize = (int)$input->getOption(self::BATCH_SIZE);
            $storeId = (int)$input->getOption(self::STORE_ID);

            $output->writeln('<info>Starting catalog sync...</info>');
            $output->writeln("Batch size: {$batchSize}");
            $output->writeln("Store ID: {$storeId}");

            if (!$this->helper->isEnabled()) {
                $output->writeln('<error>Discovery Suite is not enabled. Please enable it in configuration.</error>');
                return Command::FAILURE;
            }

            // Test API connection first
            $output->writeln('<info>Testing API connection...</info>');
            $isConnected = $this->testApiConnection($output);
            
            if (!$isConnected) {
                $output->writeln('<error>API connection failed. Please check your configuration.</error>');
                return Command::FAILURE;
            }

            $output->writeln('<info>API connection successful!</info>');

            // Sync products in batches
            $totalSynced = $this->syncProducts($batchSize, $storeId, $output);

            $output->writeln("<info>Catalog sync completed successfully! Synced {$totalSynced} products.</info>");
            return Command::SUCCESS;

        } catch (\Exception $e) {
            $output->writeln('<error>Error during catalog sync: ' . $e->getMessage() . '</error>');
            return Command::FAILURE;
        }
    }

    /**
     * Test API connection
     *
     * @param OutputInterface $output
     * @return bool
     */
    private function testApiConnection(OutputInterface $output): bool
    {
        try {
            $searchEndpoint = $this->helper->getApiBaseUrl() . ':' . $this->helper->getSearchServicePort() . '/health/';
            $response = $this->httpClient->get($searchEndpoint);
            
            if (!empty($response['status']) && $response['status'] === 'healthy') {
                return true;
            }
            
            return false;
        } catch (\Exception $e) {
            $output->writeln('<comment>API connection test failed: ' . $e->getMessage() . '</comment>');
            return false;
        }
    }

    /**
     * Sync products to discovery service
     *
     * @param int $batchSize
     * @param int $storeId
     * @param OutputInterface $output
     * @return int
     */
    private function syncProducts(int $batchSize, int $storeId, OutputInterface $output): int
    {
        $totalSynced = 0;
        $page = 1;
        
        try {
            // Set store scope
            $this->storeManager->setCurrentStore($storeId);
            $store = $this->storeManager->getStore($storeId);
            
            $output->writeln('<info>Loading products from store: ' . $store->getName() . '</info>');
            
            do {
                // Load products in batches
                $collection = $this->productCollectionFactory->create();
                $collection->addAttributeToSelect('*')
                    ->addStoreFilter($storeId)
                    ->addAttributeToFilter('status', Status::STATUS_ENABLED)
                    ->addAttributeToFilter('visibility', ['in' => [
                        Visibility::VISIBILITY_IN_CATALOG,
                        Visibility::VISIBILITY_IN_SEARCH,
                        Visibility::VISIBILITY_BOTH
                    ]])
                    ->setPageSize($batchSize)
                    ->setCurPage($page);
                
                $products = $collection->getItems();
                
                if (empty($products)) {
                    break;
                }
                
                $output->writeln("<info>Processing batch {$page} - " . count($products) . " products...</info>");
                
                // Prepare batch data
                $batchData = [];
                foreach ($products as $product) {
                    $productData = $this->formatProductForApi($product, $store);
                    if ($productData) {
                        $batchData[] = $productData;
                    }
                }
                
                if (!empty($batchData)) {
                    // Send batch to AI service
                    $synced = $this->sendProductBatch($batchData, $output);
                    $totalSynced += $synced;
                    
                    $output->writeln("<info>Synced {$synced} products from batch {$page}</info>");
                }
                
                $page++;
                
                // Small delay to prevent overwhelming the API
                usleep(100000); // 0.1 second
                
            } while (count($products) == $batchSize);
            
        } catch (\Exception $e) {
            $output->writeln('<error>Error during product sync: ' . $e->getMessage() . '</error>');
            throw $e;
        }
        
        return $totalSynced;
    }

    /**
     * Format product data for API
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param \Magento\Store\Model\Store $store
     * @return array|null
     */
    private function formatProductForApi($product, $store): ?array
    {
        try {
            // Get stock information
            $stockItem = $this->stockRegistry->getStockItem($product->getId());
            
            // Get product URL
            $productUrl = $product->getProductUrl();
            
            // Get product image - try multiple sources
            $imageUrl = $this->getProductImageUrl($product);
            
            // Get categories
            $categoryIds = $product->getCategoryIds();
            $categories = [];
            if (!empty($categoryIds)) {
                foreach ($categoryIds as $categoryId) {
                    try {
                        $category = $this->storeManager->getStore()->getGroupId();
                        $categories[] = $categoryId;
                    } catch (\Exception $e) {
                        // Skip invalid categories
                    }
                }
            }
            
            // Format product data according to AI service expectations
            $productData = [
                'id' => $product->getId(),
                'sku' => $product->getSku(),
                'name' => $product->getName(),
                'description' => $product->getDescription() ?: $product->getShortDescription(),
                'short_description' => $product->getShortDescription(),
                'price' => $this->getProductPrice($product, $store),
                'special_price' => $product->getSpecialPrice() ? (float)$product->getSpecialPrice() : null,
                'final_price' => $this->getProductFinalPrice($product, $store),
                'currency' => $store->getCurrentCurrency()->getCode(),
                'url' => $productUrl,
                'image_url' => $imageUrl,
                'categories' => $categories,
                'attributes' => [
                    'type' => $product->getTypeId(),
                    'weight' => $product->getWeight(),
                    'manufacturer' => $product->getAttributeText('manufacturer'),
                    'color' => $product->getAttributeText('color'),
                    'size' => $product->getAttributeText('size'),
                ],
                'stock' => [
                    'qty' => $stockItem ? (float)$stockItem->getQty() : 0,
                    'is_in_stock' => $stockItem ? (bool)$stockItem->getIsInStock() : false,
                    'manage_stock' => $stockItem ? (bool)$stockItem->getManageStock() : false,
                ],
                'status' => $product->getStatus(),
                'visibility' => $product->getVisibility(),
                'created_at' => $product->getCreatedAt(),
                'updated_at' => $product->getUpdatedAt(),
                'store_id' => $store->getId(),
                'website_id' => $store->getWebsiteId()
            ];
            
            return $productData;
            
        } catch (\Exception $e) {
            // Log error but continue with other products
            return null;
        }
    }

    /**
     * Send product batch to AI service
     *
     * @param array $batchData
     * @param OutputInterface $output
     * @return int
     */
    private function sendProductBatch(array $batchData, OutputInterface $output): int
    {
        try {
            $indexEndpoint = '/api/v1/index/products';
            
            $payload = [
                'products' => $batchData
            ];
            
            // Check if search service is available before sending
            if (!$this->helper->isServiceAvailable('search')) {
                $output->writeln('<error>Search service (port 7001) is not available. Please start AI services first.</error>');
                return 0;
            }
            
            // Use the injected HTTP client (now configured for search service via DI)
            $response = $this->httpClient->post($indexEndpoint, $payload);
            
            if (isset($response['success']) && $response['success']) {
                return isset($response['indexed_count']) ? (int)$response['indexed_count'] : count($batchData);
            } else {
                $error = isset($response['message']) ? $response['message'] : 'Unknown error';
                $output->writeln("<error>API Error: {$error}</error>");
                return 0;
            }
            
        } catch (\Exception $e) {
            $output->writeln('<error>Failed to send batch: ' . $e->getMessage() . '</error>');
            return 0;
        }
    }

    /**
     * Get product price with proper calculation
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param \Magento\Store\Model\Store $store
     * @return float
     */
    private function getProductPrice($product, $store = null)
    {
        try {
            // Try different price methods
            $price = $product->getPrice();
            
            if (!$price || $price <= 0) {
                // Try final price
                $price = $product->getFinalPrice();
            }
            
            if (!$price || $price <= 0) {
                // Try price index
                $priceModel = $product->getPriceModel();
                $price = $priceModel->getPrice($product);
            }
            
            if (!$price || $price <= 0) {
                // Try formatted price helper
                $priceText = $this->priceHelper->currency($product->getFinalPrice(), false, false);
                $price = (float)filter_var($priceText, FILTER_SANITIZE_NUMBER_FLOAT, FILTER_FLAG_ALLOW_FRACTION);
            }
            
            return (float)$price;
        } catch (\Exception $e) {
            return 0.0;
        }
    }

    /**
     * Get product final price
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param \Magento\Store\Model\Store $store
     * @return float
     */
    private function getProductFinalPrice($product, $store = null)
    {
        try {
            return (float)$product->getFinalPrice();
        } catch (\Exception $e) {
            return 0.0;
        }
    }

    /**
     * Get product image URL with fallback options
     *
     * @param \Magento\Catalog\Model\Product $product
     * @return string
     */
    private function getProductImageUrl($product)
    {
        $imageUrl = '';
        
        try {
            // Try base image first
            $imageUrl = $this->imageHelper->init($product, 'product_base_image')->getUrl();
            
            // Check if it's a placeholder image
            if (!$imageUrl || strpos($imageUrl, 'placeholder') !== false) {
                // Try small image
                $imageUrl = $this->imageHelper->init($product, 'product_small_image')->getUrl();
            }
            
            // If still placeholder or empty, try thumbnail
            if (!$imageUrl || strpos($imageUrl, 'placeholder') !== false) {
                $imageUrl = $this->imageHelper->init($product, 'product_thumbnail')->getUrl();
            }
            
            // Try getting image from media gallery
            if (!$imageUrl || strpos($imageUrl, 'placeholder') !== false) {
                $galleryImages = $product->getMediaGalleryImages();
                if ($galleryImages && count($galleryImages) > 0) {
                    foreach ($galleryImages as $image) {
                        if ($image->getUrl() && strpos($image->getUrl(), 'placeholder') === false) {
                            $imageUrl = $image->getUrl();
                            break;
                        }
                    }
                }
            }
            
            // Last resort: try image attribute directly
            if (!$imageUrl || strpos($imageUrl, 'placeholder') !== false) {
                $imageAttribute = $product->getImage();
                if ($imageAttribute && $imageAttribute !== 'no_selection') {
                    $mediaUrl = $this->storeManager->getStore()->getBaseUrl(\Magento\Framework\UrlInterface::URL_TYPE_MEDIA);
                    $imageUrl = $mediaUrl . 'catalog/product' . $imageAttribute;
                }
            }
            
        } catch (\Exception $e) {
            // If all fails, return empty string
            $imageUrl = '';
        }
        
        return $imageUrl;
    }

}