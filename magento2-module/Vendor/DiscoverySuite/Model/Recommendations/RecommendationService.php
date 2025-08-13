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
            
            // Process ML-powered recommendations response
            if ($response && isset($response['recommendations'])) {
                $metadata = $response['recommendation_metadata'] ?? [];
                
                // Add ML insights to each recommendation (only if provided by AI service)
                foreach ($response['recommendations'] as &$recommendation) {
                    // Only add ML metadata if it exists in the response
                    if (!isset($recommendation['ml_powered'])) {
                        $recommendation['ml_powered'] = false; // Default to false if not specified
                    }
                    if (!isset($recommendation['personalized'])) {
                        $recommendation['personalized'] = false;
                    }
                    if (isset($recommendation['algorithm'])) {
                        $recommendation['algorithm_used'] = $recommendation['algorithm'];
                    }
                    if (isset($recommendation['confidence'])) {
                        $recommendation['confidence_score'] = $recommendation['confidence'];
                    }
                    
                    // Add user-friendly reason
                    if (empty($recommendation['reason'])) {
                        $recommendation['reason'] = $this->generateReasonText(
                            $recommendation['algorithm_used'],
                            $recommendation['personalized']
                        );
                    }
                    
                    // Ensure Magento compatibility
                    $recommendation['product_id'] = $recommendation['product_id'] ?? $recommendation['sku'] ?? '';
                    $recommendation['name'] = $recommendation['name'] ?? $recommendation['title'] ?? '';
                    $recommendation['image_url'] = $recommendation['image_url'] ?? '';
                    $recommendation['url'] = $recommendation['url'] ?? '';
                    $recommendation['price'] = $recommendation['price'] ?? 0;
                }
                
                // Add overall ML metadata (only if provided by AI service)
                $response['ml_insights'] = [
                    'ml_powered' => $metadata['ml_powered'] ?? false,
                    'personalized' => $metadata['personalized'] ?? false,
                    'algorithms_used' => $metadata['algorithms_used'] ?? [],
                    'avg_confidence' => $metadata['avg_confidence'] ?? 0,
                    'real_time_learning' => $this->helper->isRealTimeLearningEnabled(),
                    'collaborative_filtering' => $this->helper->isCollaborativeFilteringEnabled(),
                    'content_based' => $this->helper->isContentBasedEnabled()
                ];
                
                $this->logger->info('ML recommendations processed', [
                    'user_id' => $userId,
                    'context' => $context,
                    'count' => count($response['recommendations']),
                    'ml_powered' => $metadata['ml_powered'] ?? false
                ]);
                
                return $response;
            }
            
            return $response;

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Recommendations API error',
                ['error' => $e->getMessage(), 'user_id' => $userId, 'context' => $context]
            );
            
            return [
                'recommendations' => [],
                'total' => 0,
                'user_id' => $userId,
                'context' => $context,
                'error' => 'Recommendations service failed: ' . $e->getMessage(),
                'ai_enhanced' => false
            ];
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
     * Generate user-friendly reason text for recommendations
     *
     * @param string $algorithm
     * @param bool $personalized
     * @return string
     */
    private function generateReasonText(string $algorithm, bool $personalized): string
    {
        $reasons = [
            'collaborative_filtering' => $personalized 
                ? 'Customers with similar tastes also liked this'
                : 'Popular among customers with similar preferences',
            'content_based' => 'Similar products based on features and attributes',
            'hybrid' => $personalized 
                ? 'Personally recommended based on your preferences'
                : 'Recommended based on advanced AI analysis',
            'popularity' => 'Popular among all customers',
            'trending' => 'Trending product right now',
            'similar' => 'Similar to products you viewed'
        ];

        return $reasons[$algorithm] ?? ($personalized ? 'Personally recommended for you' : 'Recommended product');
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