<?php
/**
 * DiscoverySuite Recommendation Service
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Model\Recommendations;

use Vendor\DiscoverySuite\Api\RecommendationInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Psr\Log\LoggerInterface;

class RecommendationService implements RecommendationInterface
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
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param Data $helper
     * @param HttpClient $httpClient
     * @param LoggerInterface $logger
     */
    public function __construct(
        Data $helper,
        HttpClient $httpClient,
        LoggerInterface $logger
    ) {
        $this->helper = $helper;
        $this->httpClient = $httpClient;
        $this->logger = $logger;
    }

    /**
     * Get product recommendations
     *
     * @param string $userId
     * @param string $context
     * @param int $limit
     * @param array $filters
     * @return array
     */
    public function getRecommendations(string $userId, string $context, int $limit = 12, array $filters = []): array
    {
        if (!$this->helper->isRecommendationsEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('recommendation', '/api/v1/recommendations/');
            
            // Map Magento contexts to API contexts
            $contextMap = [
                'product_view' => 'product_view',
                'category_view' => 'category_view', 
                'homepage' => 'home',
                'cart' => 'cart',
                'checkout' => 'checkout',
                'search' => 'search',
                'wishlist' => 'wishlist'
            ];
            $apiContext = $contextMap[$context] ?? $context;
            
            $requestData = [
                'user_id' => $userId,
                'context' => $apiContext,
                'limit' => $limit,
                'filters' => is_array($filters) && !empty($filters) ? $filters : (object)[] // Ensure object, not array
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return $response['recommendations'] ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Recommendations API error',
                ['error' => $e->getMessage(), 'user_id' => $userId, 'context' => $context]
            );
            return [];
        }
    }

    /**
     * Get similar products
     *
     * @param int $productId
     * @param int $limit
     * @return array
     */
    public function getSimilarProducts(int $productId, int $limit = 12): array
    {
        if (!$this->helper->isRecommendationsEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('recommendation', '/api/v1/recommendations/similar');
            
            $requestData = [
                'product_id' => $productId,
                'limit' => $limit
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return $response['recommendations'] ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Similar products API error',
                ['error' => $e->getMessage(), 'product_id' => $productId]
            );
            return [];
        }
    }

    /**
     * Track user interaction
     *
     * @param string $userId
     * @param int $productId
     * @param string $action
     * @param array $context
     * @return bool
     */
    public function trackInteraction(string $userId, int $productId, string $action, array $context = []): bool
    {
        if (!$this->helper->isEnabled()) {
            return false;
        }

        try {
            $endpoint = $this->helper->getServiceUrl('recommendation', '/api/v1/interactions/');
            
            $requestData = [
                'user_id' => $userId,
                'product_id' => $productId,
                'action' => $action,
                'context' => $context,
                'timestamp' => time()
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return isset($response['success']) && $response['success'] === true;

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Interaction tracking error',
                [
                    'error' => $e->getMessage(), 
                    'user_id' => $userId, 
                    'product_id' => $productId, 
                    'action' => $action
                ]
            );
            return false;
        }
    }
}