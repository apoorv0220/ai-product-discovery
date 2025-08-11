<?php
/**
 * DiscoverySuite Listing Optimizer Model
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Model\Listing;

use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Magento\Catalog\Model\ResourceModel\Product\CollectionFactory;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;
use Psr\Log\LoggerInterface;

class ListingOptimizer
{
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
     * @var ScopeConfigInterface
     */
    private $scopeConfig;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param Data $helper
     * @param HttpClient $httpClient
     * @param CollectionFactory $productCollectionFactory
     * @param ScopeConfigInterface $scopeConfig
     * @param LoggerInterface $logger
     */
    public function __construct(
        Data $helper,
        HttpClient $httpClient,
        CollectionFactory $productCollectionFactory,
        ScopeConfigInterface $scopeConfig,
        LoggerInterface $logger
    ) {
        $this->helper = $helper;
        $this->httpClient = $httpClient;
        $this->productCollectionFactory = $productCollectionFactory;
        $this->scopeConfig = $scopeConfig;
        $this->logger = $logger;
    }

    /**
     * Check if listing optimizer is enabled
     *
     * @param int|null $storeId
     * @return bool
     */
    public function isEnabled($storeId = null): bool
    {
        return $this->helper->isEnabled($storeId) && $this->scopeConfig->isSetFlag(
            'discovery_suite/listing/enabled',
            ScopeInterface::SCOPE_STORE,
            $storeId
        );
    }

    /**
     * Optimize product listing order
     *
     * @param array $productIds
     * @param string $context
     * @param array $filters
     * @return array
     */
    public function optimizeListingOrder(array $productIds, string $context = 'category', array $filters = []): array
    {
        if (!$this->isEnabled()) {
            return $productIds;
        }

        try {
            $endpoint = $this->helper->getServiceUrl('listing_optimizer', '/api/v1/optimize/');
            
            $requestData = [
                'product_ids' => $productIds,
                'context' => $context,
                'filters' => $filters,
                'timestamp' => time()
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            if (!empty($response['optimized_order'])) {
                return $response['optimized_order'];
            }

        } catch (\Exception $e) {
            $this->logger->error('Listing optimization failed', [
                'error' => $e->getMessage(),
                'context' => $context,
                'product_count' => count($productIds)
            ]);
        }

        return $productIds;
    }

    /**
     * Get dynamic filters for category
     *
     * @param int $categoryId
     * @param array $context
     * @return array
     */
    public function getDynamicFilters(int $categoryId, array $context = []): array
    {
        if (!$this->isEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('listing_optimizer', '/api/v1/filters/');
            
            $requestData = [
                'category_id' => $categoryId,
                'context' => $context
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return $response['filters'] ?? [];

        } catch (\Exception $e) {
            $this->logger->error('Dynamic filters request failed', [
                'error' => $e->getMessage(),
                'category_id' => $categoryId
            ]);
        }

        return [];
    }

    /**
     * Track listing performance
     *
     * @param array $performanceData
     * @return bool
     */
    public function trackListingPerformance(array $performanceData): bool
    {
        if (!$this->isEnabled()) {
            return false;
        }

        try {
            $endpoint = $this->helper->getServiceUrl('listing_optimizer', '/api/v1/track/');
            
            $response = $this->httpClient->post($endpoint, $performanceData);
            
            return isset($response['success']) && $response['success'] === true;

        } catch (\Exception $e) {
            $this->logger->error('Listing performance tracking failed', [
                'error' => $e->getMessage()
            ]);
        }

        return false;
    }

    /**
     * Get performance insights for products
     *
     * @param array $productIds
     * @param int $days
     * @return array
     */
    public function getPerformanceInsights(array $productIds, int $days = 30): array
    {
        if (!$this->isEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('listing_optimizer', '/api/v1/insights/');
            
            $requestData = [
                'product_ids' => $productIds,
                'days' => $days
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return $response['insights'] ?? [];

        } catch (\Exception $e) {
            $this->logger->error('Performance insights request failed', [
                'error' => $e->getMessage(),
                'product_count' => count($productIds)
            ]);
        }

        return [];
    }
}