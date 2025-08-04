<?php
/**
 * DiscoverySuite Listing Optimizer Service
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Model\Listing;

use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Magento\Framework\Exception\LocalizedException;
use Magento\Store\Model\StoreManagerInterface;
use Magento\Catalog\Model\ResourceModel\Product\Collection as ProductCollection;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;
use Psr\Log\LoggerInterface;

class ListingOptimizer
{
    /**
     * @var HttpClient
     */
    private $httpClient;

    /**
     * @var StoreManagerInterface
     */
    private $storeManager;

    /**
     * @var ScopeConfigInterface
     */
    private $scopeConfig;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Configuration paths
     */
    const XML_PATH_SMART_LISTINGS_ENABLED = 'discovery_suite/smart_listings/enabled';
    const XML_PATH_AUTO_SORT_ENABLED = 'discovery_suite/smart_listings/auto_sort_enabled';
    const XML_PATH_DYNAMIC_FILTERS_ENABLED = 'discovery_suite/smart_listings/dynamic_filters_enabled';
    const XML_PATH_MERCHANDISING_ENABLED = 'discovery_suite/smart_listings/merchandising_enabled';

    /**
     * @param HttpClient $httpClient
     * @param StoreManagerInterface $storeManager
     * @param ScopeConfigInterface $scopeConfig
     * @param LoggerInterface $logger
     */
    public function __construct(
        HttpClient $httpClient,
        StoreManagerInterface $storeManager,
        ScopeConfigInterface $scopeConfig,
        LoggerInterface $logger
    ) {
        $this->httpClient = $httpClient;
        $this->storeManager = $storeManager;
        $this->scopeConfig = $scopeConfig;
        $this->logger = $logger;
    }

    /**
     * Optimize product collection using AI ranking
     *
     * @param ProductCollection $collection
     * @param array $context
     * @return ProductCollection
     */
    public function optimizeCollection(ProductCollection $collection, array $context = []): ProductCollection
    {
        if (!$this->isEnabled() || !$this->isAutoSortEnabled()) {
            return $collection;
        }

        try {
            $storeId = $context['store_id'] ?? $this->storeManager->getStore()->getId();
            $categoryId = $context['category_id'] ?? null;
            $productIds = $collection->getAllIds();

            if (empty($productIds)) {
                return $collection;
            }

            // Get AI ranking from listing optimizer service
            $rankingData = $this->getAIRanking($productIds, $categoryId, $storeId, $context);

            if (!empty($rankingData['ranking'])) {
                $this->applyRanking($collection, $rankingData['ranking']);
            }

            return $collection;

        } catch (\Exception $e) {
            $this->logger->error('Listing optimization error', [
                'category_id' => $context['category_id'] ?? null,
                'product_count' => $collection->getSize(),
                'error' => $e->getMessage()
            ]);

            return $collection;
        }
    }

    /**
     * Get AI ranking for products
     *
     * @param array $productIds
     * @param int|null $categoryId
     * @param int $storeId
     * @param array $context
     * @return array
     */
    public function getAIRanking(array $productIds, ?int $categoryId, int $storeId, array $context = []): array
    {
        try {
            $requestData = [
                'product_ids' => $productIds,
                'category_id' => $categoryId,
                'store_id' => $storeId,
                'context' => $context,
                'algorithm' => $context['algorithm'] ?? 'mixed'
            ];

            return $this->httpClient->post('/ranking/products', $requestData);

        } catch (LocalizedException $e) {
            $this->logger->error('AI ranking request failed', [
                'product_count' => count($productIds),
                'category_id' => $categoryId,
                'error' => $e->getMessage()
            ]);

            return ['ranking' => []];
        }
    }

    /**
     * Apply AI ranking to product collection
     *
     * @param ProductCollection $collection
     * @param array $ranking
     * @return void
     */
    private function applyRanking(ProductCollection $collection, array $ranking): void
    {
        // Create ORDER BY FIELD clause to maintain AI ranking order
        $rankedIds = array_column($ranking, 'product_id');
        
        if (!empty($rankedIds)) {
            $orderExpression = 'FIELD(e.entity_id, ' . implode(',', $rankedIds) . ')';
            $collection->getSelect()->order(new \Zend_Db_Expr($orderExpression));
        }
    }

    /**
     * Get dynamic filters for category
     *
     * @param int|null $categoryId
     * @param int|null $storeId
     * @return array
     */
    public function getDynamicFilters(?int $categoryId, ?int $storeId = null): array
    {
        if (!$this->isDynamicFiltersEnabled()) {
            return [];
        }

        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $requestData = [
                'category_id' => $categoryId,
                'store_id' => $storeId
            ];

            $response = $this->httpClient->get('/filters/dynamic', $requestData);

            return $response['filters'] ?? [];

        } catch (LocalizedException $e) {
            $this->logger->error('Dynamic filters request failed', [
                'category_id' => $categoryId,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * Get merchandising rules for category
     *
     * @param int|null $categoryId
     * @param int|null $storeId
     * @return array
     */
    public function getMerchandisingRules(?int $categoryId, ?int $storeId = null): array
    {
        if (!$this->isMerchandisingEnabled()) {
            return [];
        }

        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $requestData = [
                'category_id' => $categoryId,
                'store_id' => $storeId
            ];

            $response = $this->httpClient->get('/merchandising/rules', $requestData);

            return $response['rules'] ?? [];

        } catch (LocalizedException $e) {
            $this->logger->error('Merchandising rules request failed', [
                'category_id' => $categoryId,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * Boost product in category
     *
     * @param int $productId
     * @param int|null $categoryId
     * @param float $boostFactor
     * @param int|null $storeId
     * @return bool
     */
    public function boostProduct(int $productId, ?int $categoryId, float $boostFactor, ?int $storeId = null): bool
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $requestData = [
                'product_id' => $productId,
                'category_id' => $categoryId,
                'boost_factor' => $boostFactor,
                'store_id' => $storeId,
                'action' => 'boost'
            ];

            $response = $this->httpClient->post('/merchandising/boost', $requestData);

            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Product boost failed', [
                'product_id' => $productId,
                'category_id' => $categoryId,
                'boost_factor' => $boostFactor,
                'error' => $e->getMessage()
            ]);

            return false;
        }
    }

    /**
     * Pin product to position in category
     *
     * @param int $productId
     * @param int|null $categoryId
     * @param int $position
     * @param int|null $storeId
     * @return bool
     */
    public function pinProduct(int $productId, ?int $categoryId, int $position, ?int $storeId = null): bool
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $requestData = [
                'product_id' => $productId,
                'category_id' => $categoryId,
                'position' => $position,
                'store_id' => $storeId,
                'action' => 'pin'
            ];

            $response = $this->httpClient->post('/merchandising/pin', $requestData);

            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Product pin failed', [
                'product_id' => $productId,
                'category_id' => $categoryId,
                'position' => $position,
                'error' => $e->getMessage()
            ]);

            return false;
        }
    }

    /**
     * Hide product from category
     *
     * @param int $productId
     * @param int|null $categoryId
     * @param int|null $storeId
     * @return bool
     */
    public function hideProduct(int $productId, ?int $categoryId, ?int $storeId = null): bool
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $requestData = [
                'product_id' => $productId,
                'category_id' => $categoryId,
                'store_id' => $storeId,
                'action' => 'hide'
            ];

            $response = $this->httpClient->post('/merchandising/hide', $requestData);

            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Product hide failed', [
                'product_id' => $productId,
                'category_id' => $categoryId,
                'error' => $e->getMessage()
            ]);

            return false;
        }
    }

    /**
     * Sync product performance data
     *
     * @param array $productIds
     * @param int|null $storeId
     * @return bool
     */
    public function syncProductPerformance(array $productIds = [], ?int $storeId = null): bool
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $requestData = [
                'product_ids' => $productIds,
                'store_id' => $storeId,
                'sync_type' => 'performance'
            ];

            $response = $this->httpClient->post('/sync/performance', $requestData);

            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Performance sync failed', [
                'product_count' => count($productIds),
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return false;
        }
    }

    /**
     * Check if smart listings are enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_SMART_LISTINGS_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if auto sort is enabled
     *
     * @return bool
     */
    public function isAutoSortEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_AUTO_SORT_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if dynamic filters are enabled
     *
     * @return bool
     */
    public function isDynamicFiltersEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_DYNAMIC_FILTERS_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if merchandising is enabled
     *
     * @return bool
     */
    public function isMerchandisingEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_MERCHANDISING_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }
}