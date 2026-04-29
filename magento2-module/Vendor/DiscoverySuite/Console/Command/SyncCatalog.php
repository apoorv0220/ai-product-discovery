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
use Magento\Catalog\Api\CategoryRepositoryInterface;
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
     * @var CategoryRepositoryInterface
     */
    private $categoryRepository;

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
     * @param CategoryRepositoryInterface $categoryRepository
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
        CategoryRepositoryInterface $categoryRepository,
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
        $this->categoryRepository = $categoryRepository;
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
            $searchEndpoint = $this->helper->getServiceUrl('search', '/health/');
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
     * Extract a select attribute value, trying multiple codes if needed
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param string $attributeCode
     * @param array $alternativeCodes
     * @return mixed|null
     */
    private function extractSelectAttribute($product, $attributeCode, array $alternativeCodes = []): ?string
    {
        // Try primary attribute code first, then alternatives
        $codesToTry = array_merge([$attributeCode], $alternativeCodes);
        
        foreach ($codesToTry as $code) {
            try {
                // Check if attribute exists before calling getAttributeText()
                $attribute = $product->getResource()->getAttribute($code);
                if (!$attribute || !$attribute->getId()) {
                    // Attribute doesn't exist, try next code
                    continue;
                }
                
                // Try getAttributeText() which returns the label
                $value = $product->getAttributeText($code);
                
                if ($value !== false && $value !== null && $value !== '') {
                    return (string)$value;
                }
                
                // If getAttributeText() returns false, try getData() to get raw value
                $rawValue = $product->getData($code);
                
                if ($rawValue && $rawValue !== '' && $rawValue !== '0' && $rawValue !== false) {
                    // If raw value is numeric (option ID), the attribute exists but might need reload
                    if (is_numeric($rawValue)) {
                        // Attribute exists but getAttributeText failed - try again
                        $value = $product->getAttributeText($code);
                        if ($value !== false && $value !== null && $value !== '') {
                            return (string)$value;
                        }
                        // If still false, attribute exists but is empty - continue to next code
                        continue;
                    }
                    // If raw value is a string, use it directly
                    return (string)$rawValue;
                }
            } catch (\Exception $e) {
                // Attribute doesn't exist or error accessing it, try next code
                continue;
            }
        }
        
        return null;
    }

    /**
     * Get variant attributes from configurable product children
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param \Magento\Store\Model\Store|null $store
     * @return array Array with 'color' and 'size' keys containing unique values from variants
     */
    private function getVariantAttributes($product, $store = null): array
    {
        $variantAttrs = [
            'color' => [],
            'size' => []
        ];
        
        try {
            // Check if product is configurable
            if ($product->getTypeId() !== 'configurable') {
                return $variantAttrs;
            }
            
            // Get child products (variants)
            $typeInstance = $product->getTypeInstance();
            if (!$typeInstance || !method_exists($typeInstance, 'getUsedProducts')) {
                return $variantAttrs;
            }
            
            // Get used products (variants) - getUsedProducts($product, $requiredAttributeIds = null)
            // Pass null for attributes to get all variants
            // Store context is already set via setCurrentStore() in syncProducts()
            $childProducts = $typeInstance->getUsedProducts($product, null);
            
            if (empty($childProducts)) {
                return $variantAttrs;
            }
            
            // Collect color and size from all variants
            $colors = [];
            $sizes = [];
            
            foreach ($childProducts as $child) {
                // Extract color from variant
                $color = $this->extractSelectAttribute($child, 'color', ['colour', 'Color', 'Colour']);
                if ($color && !in_array($color, $colors)) {
                    $colors[] = $color;
                }
                
                // Extract size from variant
                $size = $this->extractSelectAttribute($child, 'size', ['Size']);
                if ($size && !in_array($size, $sizes)) {
                    $sizes[] = $size;
                }
            }
            
            $variantAttrs['color'] = $colors;
            $variantAttrs['size'] = $sizes;
            
        } catch (\Exception $e) {
            // Silently fail - variant attributes are optional
        }
        
        return $variantAttrs;
    }

    /**
     * Extract product attributes with proper handling for different attribute types
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param \Magento\Store\Model\Store|null $store
     * @return array
     */
    private function extractProductAttributes($product, $store = null): array
    {
        $attributes = [
            'type' => $product->getTypeId(),
            'weight' => $product->getWeight(),
        ];
        
        // For configurable products, get color/size from variants
        $variantAttrs = $this->getVariantAttributes($product, $store);
        
        // Merge variant attributes into main attributes if they exist
        if (!empty($variantAttrs['color'])) {
            $attributes['color'] = $variantAttrs['color'];
        }
        if (!empty($variantAttrs['size'])) {
            $attributes['size'] = $variantAttrs['size'];
        }

        // List of attributes to extract with their expected types
        $attributeConfig = [
            'manufacturer' => 'select',  // Brand dropdown
            'color' => 'select',         // Color dropdown (typically select in Magento)
            'size' => 'select',          // Size dropdown (typically select in Magento)
            'material' => 'multiselect', // Multiselect attribute
            'pattern' => 'select',       // Pattern dropdown
            'climate' => 'multiselect',  // Climate multiselect
        ];
        
        // Alternative attribute codes to try (for color/size that might have different names)
        $alternativeCodes = [
            'color' => ['colour', 'Color', 'Colour'],
            'size' => ['Size']
        ];

        foreach ($attributeConfig as $attributeCode => $attributeType) {
            try {
                // Skip color/size if we already have variant attributes (for configurable products)
                // This prevents overwriting variant arrays with parent values
                if (in_array($attributeCode, ['color', 'size']) && isset($attributes[$attributeCode])) {
                    continue;
                }
                
                $value = null;

                switch ($attributeType) {
                    case 'select':
                        // For dropdown/select attributes, try multiple methods and codes
                        $value = $this->extractSelectAttribute($product, $attributeCode, $alternativeCodes[$attributeCode] ?? []);
                        break;

                    case 'multiselect':
                        // For multiselect, getAttributeText() returns array of option texts
                        // Check if attribute exists first to avoid errors
                        $attribute = $product->getResource()->getAttribute($attributeCode);
                        if ($attribute && $attribute->getId()) {
                            try {
                                $value = $product->getAttributeText($attributeCode);
                                // getAttributeText() can return false for empty multiselect
                                if ($value === false) {
                                    $value = null;
                                } elseif ($value && !is_array($value)) {
                                    // Ensure it's an array or convert to array
                                    $value = [$value];
                                } elseif (is_array($value)) {
                                    // Filter out empty/false values from array
                                    $value = array_filter($value, function($v) {
                                        return $v !== null && $v !== '' && $v !== false;
                                    });
                                    if (empty($value)) {
                                        $value = null;
                                    } else {
                                        $value = array_values($value); // Re-index array
                                    }
                                }
                            } catch (\Exception $e) {
                                // Attribute access failed, set to null
                                $value = null;
                            }
                        } else {
                            $value = null;
                        }
                        break;

                    case 'text':
                    default:
                        // For text inputs, use getData() instead of getAttributeText()
                        $rawValue = $product->getData($attributeCode);
                        if ($rawValue && $rawValue !== '' && $rawValue !== false) {
                            $value = $rawValue;
                        }
                        // Fallback to getAttributeText() for select attributes that might be configured as text
                        // Check if attribute exists first to avoid errors
                        if (!$value || $value === false) {
                            $attribute = $product->getResource()->getAttribute($attributeCode);
                            if ($attribute && $attribute->getId()) {
                                try {
                                    $value = $product->getAttributeText($attributeCode);
                                    // If getAttributeText returns false for empty, convert to null
                                    if ($value === false) {
                                        $value = null;
                                    }
                                } catch (\Exception $e) {
                                    // Attribute access failed, keep existing value or null
                                    $value = null;
                                }
                            }
                        }
                        break;
                }

                // Only include non-empty values
                // Filter out: null, empty strings, false, empty arrays, and arrays with only empty/false values
                $shouldInclude = false;
                if ($value !== null && $value !== '' && $value !== false) {
                    if (is_array($value)) {
                        // For arrays, check if any element is non-empty
                        $filtered = array_filter($value, function($v) {
                            return $v !== null && $v !== '' && $v !== false;
                        });
                        $shouldInclude = !empty($filtered);
                        if ($shouldInclude) {
                            $value = array_values($filtered); // Re-index array
                        }
                    } else {
                        $shouldInclude = true;
                    }
                }
                
                if ($shouldInclude) {
                    $attributes[$attributeCode] = $value;
                }

            } catch (\Exception $e) {
                // Skip problematic attributes but continue with others
                continue;
            }
        }
        
        // For configurable products, add aggregated color/size from variants if not already set
        if ($product->getTypeId() === 'configurable') {
            // Add color from variants if not already extracted from parent
            if (empty($attributes['color']) && !empty($variantAttrs['color'])) {
                // If multiple colors, store as array; if single, store as string
                if (count($variantAttrs['color']) === 1) {
                    $attributes['color'] = $variantAttrs['color'][0];
                } elseif (count($variantAttrs['color']) > 1) {
                    $attributes['color'] = $variantAttrs['color'];
                }
            }
            
            // Add size from variants if not already extracted from parent
            if (empty($attributes['size']) && !empty($variantAttrs['size'])) {
                // If multiple sizes, store as array; if single, store as string
                if (count($variantAttrs['size']) === 1) {
                    $attributes['size'] = $variantAttrs['size'][0];
                } elseif (count($variantAttrs['size']) > 1) {
                    $attributes['size'] = $variantAttrs['size'];
                }
            }
        }

        return $attributes;
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
            
            // Get categories with names
            $categoryIds = $product->getCategoryIds();
            $categories = [];
            if (!empty($categoryIds)) {
                foreach ($categoryIds as $categoryId) {
                    try {
                        $category = $this->categoryRepository->get($categoryId, $store->getId());
                        $categories[] = [
                            'id' => (string)$categoryId,
                            'name' => $category->getName()
                        ];
                    } catch (\Exception $e) {
                        // Fallback to ID only if category not found
                        $categories[] = (string)$categoryId;
                    }
                }
            }
            
                // Format product data according to AI service expectations
            $productData = [
                'id' => (string)$product->getId(),
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
                'attributes' => $this->extractProductAttributes($product, $store),
                'stock' => [
                    'qty' => $stockItem ? (float)$stockItem->getQty() : 0,
                    'is_in_stock' => $stockItem ? (bool)$stockItem->getIsInStock() : false,
                    'manage_stock' => $stockItem ? (bool)$stockItem->getManageStock() : false,
                ],
                'status' => $product->getStatus(),
                'visibility' => $product->getVisibility(),
                'created_at' => $product->getCreatedAt(),
                'updated_at' => $product->getUpdatedAt(),
                'store_id' => (string)$store->getId(),
                'website_id' => (string)$store->getWebsiteId(),
                'avg_rating' => $this->getProductRating($product, $store),
                'review_count' => $this->getProductReviewCount($product, $store)
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

    /**
     * Get product average rating
     * For configurable products, reviews are typically on the parent product
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param \Magento\Store\Model\Store $store
     * @return float|null
     */
    private function getProductRating($product, $store = null)
    {
        try {
            // Try to get from product attributes directly (most common in Magento)
            // Magento stores rating_summary as a product attribute
            $ratingSummary = $product->getData('rating_summary');
            if ($ratingSummary && $ratingSummary > 0) {
                // Convert percentage to 5-star scale (Magento stores as percentage)
                return round(($ratingSummary / 100) * 5, 2);
            }
            
            // Fallback: Try getRatingSummary() method if available
            if (method_exists($product, 'getRatingSummary')) {
                $ratingSummary = $product->getRatingSummary();
                if ($ratingSummary && $ratingSummary > 0) {
                    return round(($ratingSummary / 100) * 5, 2);
                }
            }
            
            return null;
        } catch (\Exception $e) {
            // Silently fail - ratings are optional
            return null;
        }
    }

    /**
     * Get product review count
     * For configurable products, reviews are typically on the parent product
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param \Magento\Store\Model\Store $store
     * @return int
     */
    private function getProductReviewCount($product, $store = null)
    {
        try {
            // Try to get from product attributes directly (most common in Magento)
            // Magento stores reviews_count as a product attribute
            $reviewCountAttr = $product->getData('reviews_count');
            if ($reviewCountAttr && $reviewCountAttr > 0) {
                return (int)$reviewCountAttr;
            }
            
            // Fallback: Try getReviewsCount() method if available
            if (method_exists($product, 'getReviewsCount')) {
                $reviewsCount = $product->getReviewsCount();
                if ($reviewsCount && $reviewsCount > 0) {
                    return (int)$reviewsCount;
                }
            }
            
            return 0;
        } catch (\Exception $e) {
            // Silently fail - review count is optional
            return 0;
        }
    }

}