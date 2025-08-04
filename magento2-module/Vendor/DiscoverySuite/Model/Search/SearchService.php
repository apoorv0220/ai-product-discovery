<?php
/**
 * DiscoverySuite Search Service Implementation
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Model\Search;

use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Magento\Framework\Exception\LocalizedException;
use Magento\Store\Model\StoreManagerInterface;
use Magento\Catalog\Api\ProductRepositoryInterface;
use Magento\Framework\Api\SearchCriteriaBuilder;
use Psr\Log\LoggerInterface;

class SearchService implements SearchInterface
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
     * @var ProductRepositoryInterface
     */
    private $productRepository;

    /**
     * @var SearchCriteriaBuilder
     */
    private $searchCriteriaBuilder;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param HttpClient $httpClient
     * @param StoreManagerInterface $storeManager
     * @param ProductRepositoryInterface $productRepository
     * @param SearchCriteriaBuilder $searchCriteriaBuilder
     * @param LoggerInterface $logger
     */
    public function __construct(
        HttpClient $httpClient,
        StoreManagerInterface $storeManager,
        ProductRepositoryInterface $productRepository,
        SearchCriteriaBuilder $searchCriteriaBuilder,
        LoggerInterface $logger
    ) {
        $this->httpClient = $httpClient;
        $this->storeManager = $storeManager;
        $this->productRepository = $productRepository;
        $this->searchCriteriaBuilder = $searchCriteriaBuilder;
        $this->logger = $logger;
    }

    /**
     * @inheritDoc
     */
    public function search(
        string $query,
        ?int $storeId = null,
        array $filters = [],
        int $limit = 20,
        int $offset = 0
    ): array {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            
            $params = [
                'q' => $query,
                'store_id' => $storeId,
                'limit' => $limit,
                'offset' => $offset,
                'filters' => $filters
            ];

            $response = $this->httpClient->get('/search', $params);

            // Track search event
            $this->trackSearchEvent(
                $query,
                $response['total_count'] ?? 0,
                null,
                ['store_id' => $storeId, 'filters' => $filters]
            );

            return $response;

        } catch (LocalizedException $e) {
            $this->logger->error('Search API error', [
                'query' => $query,
                'error' => $e->getMessage()
            ]);
            
            // Fallback to Magento search if enabled
            return $this->fallbackSearch($query, $storeId, $filters, $limit, $offset);
        }
    }

    /**
     * @inheritDoc
     */
    public function autocomplete(
        string $query,
        ?int $storeId = null,
        int $limit = 10
    ): array {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            
            $params = [
                'q' => $query,
                'store_id' => $storeId,
                'limit' => $limit
            ];

            return $this->httpClient->get('/autocomplete', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('Autocomplete API error', [
                'query' => $query,
                'error' => $e->getMessage()
            ]);
            
            // Return empty suggestions on error
            return [
                'suggestions' => [],
                'products' => [],
                'categories' => []
            ];
        }
    }

    /**
     * @inheritDoc
     */
    public function getSuggestions(string $query, ?int $storeId = null): array
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            
            $params = [
                'q' => $query,
                'store_id' => $storeId
            ];

            return $this->httpClient->get('/suggestions', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('Suggestions API error', [
                'query' => $query,
                'error' => $e->getMessage()
            ]);
            
            return [
                'spell_correction' => null,
                'synonyms' => [],
                'related_queries' => []
            ];
        }
    }

    /**
     * @inheritDoc
     */
    public function indexProduct(int $productId, ?int $storeId = null): bool
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            
            // Get product data
            $product = $this->productRepository->getById($productId, false, $storeId);
            
            $productData = [
                'id' => $product->getId(),
                'sku' => $product->getSku(),
                'name' => $product->getName(),
                'description' => $product->getDescription(),
                'short_description' => $product->getShortDescription(),
                'price' => $product->getPrice(),
                'special_price' => $product->getSpecialPrice(),
                'status' => $product->getStatus(),
                'visibility' => $product->getVisibility(),
                'category_ids' => $product->getCategoryIds(),
                'attributes' => $this->getProductAttributes($product),
                'store_id' => $storeId,
                'updated_at' => date('Y-m-d H:i:s')
            ];

            $response = $this->httpClient->post('/index/product', $productData);
            
            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Product indexing error', [
                'product_id' => $productId,
                'error' => $e->getMessage()
            ]);
            
            return false;
        }
    }

    /**
     * @inheritDoc
     */
    public function bulkIndexProducts(array $productIds, ?int $storeId = null): bool
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            
            $productsData = [];
            foreach ($productIds as $productId) {
                try {
                    $product = $this->productRepository->getById($productId, false, $storeId);
                    $productsData[] = [
                        'id' => $product->getId(),
                        'sku' => $product->getSku(),
                        'name' => $product->getName(),
                        'description' => $product->getDescription(),
                        'short_description' => $product->getShortDescription(),
                        'price' => $product->getPrice(),
                        'special_price' => $product->getSpecialPrice(),
                        'status' => $product->getStatus(),
                        'visibility' => $product->getVisibility(),
                        'category_ids' => $product->getCategoryIds(),
                        'attributes' => $this->getProductAttributes($product),
                        'store_id' => $storeId,
                        'updated_at' => date('Y-m-d H:i:s')
                    ];
                } catch (\Exception $e) {
                    $this->logger->warning('Failed to load product for indexing', [
                        'product_id' => $productId,
                        'error' => $e->getMessage()
                    ]);
                    continue;
                }
            }

            if (empty($productsData)) {
                return false;
            }

            $response = $this->httpClient->post('/index/products/bulk', [
                'products' => $productsData
            ]);
            
            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Bulk product indexing error', [
                'product_count' => count($productIds),
                'error' => $e->getMessage()
            ]);
            
            return false;
        }
    }

    /**
     * @inheritDoc
     */
    public function removeFromIndex(int $productId, ?int $storeId = null): bool
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            
            $response = $this->httpClient->delete('/index/product', [
                'product_id' => $productId,
                'store_id' => $storeId
            ]);
            
            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Product removal from index error', [
                'product_id' => $productId,
                'error' => $e->getMessage()
            ]);
            
            return false;
        }
    }

    /**
     * @inheritDoc
     */
    public function rebuildIndex(?int $storeId = null): bool
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            
            $response = $this->httpClient->post('/index/rebuild', [
                'store_id' => $storeId
            ]);
            
            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Index rebuild error', [
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);
            
            return false;
        }
    }

    /**
     * @inheritDoc
     */
    public function getSearchAnalytics(string $period = 'week', ?int $storeId = null): array
    {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            
            $params = [
                'period' => $period,
                'store_id' => $storeId
            ];

            return $this->httpClient->get('/analytics/search', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('Search analytics error', [
                'period' => $period,
                'error' => $e->getMessage()
            ]);
            
            return [];
        }
    }

    /**
     * @inheritDoc
     */
    public function trackSearchEvent(
        string $query,
        int $resultCount,
        ?string $userId = null,
        array $metadata = []
    ): bool {
        try {
            $eventData = [
                'query' => $query,
                'result_count' => $resultCount,
                'user_id' => $userId,
                'metadata' => $metadata,
                'timestamp' => date('Y-m-d H:i:s')
            ];

            $response = $this->httpClient->post('/analytics/search/event', $eventData);
            
            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Search event tracking error', [
                'query' => $query,
                'error' => $e->getMessage()
            ]);
            
            return false;
        }
    }

    /**
     * Fallback to Magento search when AI service is unavailable
     *
     * @param string $query
     * @param int|null $storeId
     * @param array $filters
     * @param int $limit
     * @param int $offset
     * @return array
     */
    private function fallbackSearch(
        string $query,
        ?int $storeId,
        array $filters,
        int $limit,
        int $offset
    ): array {
        // Implement basic Magento search fallback
        // This is a simplified implementation
        try {
            $this->searchCriteriaBuilder
                ->addFilter('name', '%' . $query . '%', 'like')
                ->setPageSize($limit)
                ->setCurrentPage(($offset / $limit) + 1);

            $searchCriteria = $this->searchCriteriaBuilder->create();
            $searchResults = $this->productRepository->getList($searchCriteria);

            $products = [];
            foreach ($searchResults->getItems() as $product) {
                $products[] = [
                    'id' => $product->getId(),
                    'sku' => $product->getSku(),
                    'name' => $product->getName(),
                    'price' => $product->getPrice(),
                    'url' => $product->getProductUrl()
                ];
            }

            return [
                'products' => $products,
                'total_count' => $searchResults->getTotalCount(),
                'query' => $query,
                'fallback' => true
            ];

        } catch (\Exception $e) {
            $this->logger->error('Fallback search error', [
                'query' => $query,
                'error' => $e->getMessage()
            ]);
            
            return [
                'products' => [],
                'total_count' => 0,
                'query' => $query,
                'error' => 'Search unavailable'
            ];
        }
    }

    /**
     * Get product attributes for indexing
     *
     * @param \Magento\Catalog\Api\Data\ProductInterface $product
     * @return array
     */
    private function getProductAttributes($product): array
    {
        $attributes = [];
        
        try {
            $attributeSet = $product->getAttributeSetId();
            $customAttributes = $product->getCustomAttributes();
            
            foreach ($customAttributes as $attribute) {
                $attributes[$attribute->getAttributeCode()] = $attribute->getValue();
            }
            
        } catch (\Exception $e) {
            $this->logger->warning('Failed to get product attributes', [
                'product_id' => $product->getId(),
                'error' => $e->getMessage()
            ]);
        }
        
        return $attributes;
    }
}