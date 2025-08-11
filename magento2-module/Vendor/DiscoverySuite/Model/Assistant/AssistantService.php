<?php
/**
 * DiscoverySuite Assistant Service
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Model\Assistant;

use Vendor\DiscoverySuite\Api\AssistantInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Psr\Log\LoggerInterface;

class AssistantService implements AssistantInterface
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
     * Send message to conversational AI assistant
     *
     * @param string $message
     * @param string $sessionId
     * @param string|null $userId
     * @param array $contextData
     * @return array
     */
    public function chat(string $message, string $sessionId, ?string $userId = null, array $contextData = []): array
    {
        if (!$this->helper->isShoppingAssistantEnabled()) {
            return $this->getFallbackResponse($message);
        }

        try {
            $endpoint = $this->helper->getServiceUrl('shopping_assistant', '/api/v1/chat/');
            
            $requestData = [
                'message' => $message,
                'session_id' => $sessionId,
                'user_id' => $userId,
                'context_data' => $contextData
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            // Process conversational AI response
            if ($response && isset($response['message'])) {
                // Extract AI features metadata
                $aiFeatures = $response['ai_features'] ?? [];
                
                // Add Magento-specific enhancements
                $response['magento_integration'] = [
                    'ai_powered' => $aiFeatures['ai_powered'] ?? true,
                    'nlp_processing' => $aiFeatures['nlp_processing'] ?? true,
                    'context_aware' => $aiFeatures['context_aware'] ?? true,
                    'intent_detected' => $aiFeatures['intent_detected'] ?? '',
                    'confidence' => $aiFeatures['confidence'] ?? 0.8
                ];
                
                // Process suggested actions for Magento frontend
                if (isset($response['suggested_actions'])) {
                    foreach ($response['suggested_actions'] as &$action) {
                        // Add Magento-specific URLs or actions
                        switch ($action['action']) {
                            case 'search_products':
                                $action['magento_url'] = '/catalogsearch/result/';
                                break;
                            case 'browse_categories':
                                $action['magento_url'] = '/';
                                break;
                            case 'view_cart':
                                $action['magento_url'] = '/checkout/cart/';
                                break;
                        }
                    }
                }
                
                // Process product recommendations for Magento
                if (isset($response['product_recommendations'])) {
                    foreach ($response['product_recommendations'] as &$product) {
                        // Ensure Magento-compatible product URLs
                        if (isset($product['product_id'])) {
                            $product['magento_url'] = '/catalog/product/view/id/' . $product['product_id'] . '/';
                        }
                    }
                }
                
                $this->logger->info('Conversational AI response processed', [
                    'session_id' => $sessionId,
                    'user_id' => $userId,
                    'ai_features' => $response['magento_integration']
                ]);
            }
            
            return $response ?? $this->getFallbackResponse($message);

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Conversational AI error',
                ['error' => $e->getMessage(), 'message' => substr($message, 0, 100)]
            );
            return $this->getFallbackResponse($message);
        }
    }

    /**
     * Record user interaction for ML learning
     *
     * @param string $userId
     * @param string $productId
     * @param string $interactionType
     * @param array $context
     * @return bool
     */
    public function recordInteraction(string $userId, string $productId, string $interactionType, array $context = []): bool
    {
        if (!$this->helper->isRealTimeLearningEnabled()) {
            return true; // Silent success when real-time learning is disabled
        }

        try {
            $endpoint = $this->helper->getServiceUrl('recommendation', '/api/v1/interactions/');
            
            $requestData = [
                'user_id' => $userId,
                'product_id' => $productId,
                'interaction_type' => $interactionType,
                'context' => $context,
                'timestamp' => date('c')
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            $this->logger->info('User interaction recorded for ML learning', [
                'user_id' => $userId,
                'product_id' => $productId,
                'interaction_type' => $interactionType
            ]);
            
            return isset($response['success']) && $response['success'] === true;

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Interaction recording error',
                ['error' => $e->getMessage(), 'user_id' => $userId, 'product_id' => $productId]
            );
            return false; // Don't break user experience
        }
    }

    /**
     * Get conversation history
     *
     * @param string $sessionId
     * @param string|null $userId
     * @return array
     */
    public function getConversationHistory(string $sessionId, ?string $userId = null): array
    {
        if (!$this->helper->isShoppingAssistantEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('shopping_assistant', '/api/v1/conversation/history/');
            
            $response = $this->httpClient->get($endpoint, [
                'session_id' => $sessionId,
                'user_id' => $userId
            ]);
            
            return $response['conversation_history'] ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Conversation history error',
                ['error' => $e->getMessage(), 'session_id' => $sessionId]
            );
            return [];
        }
    }

    /**
     * Clear conversation session
     *
     * @param string $sessionId
     * @return bool
     */
    public function clearSession(string $sessionId): bool
    {
        if (!$this->helper->isShoppingAssistantEnabled()) {
            return true;
        }

        try {
            $endpoint = $this->helper->getServiceUrl('shopping_assistant', "/api/v1/conversation/session/{$sessionId}");
            
            $response = $this->httpClient->delete($endpoint);
            
            return isset($response['success']) && $response['success'] === true;

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Session clear error',
                ['error' => $e->getMessage(), 'session_id' => $sessionId]
            );
            return false;
        }
    }

    /**
     * Get fallback response when AI is unavailable
     *
     * @param string $message
     * @return array
     */
    private function getFallbackResponse(string $message): array
    {
        return [
            'message' => 'Hello! I\'m here to help you find products. What are you looking for?',
            'state' => 'intent_detection',
            'suggested_actions' => [
                [
                    'action' => 'search_products',
                    'label' => 'Search for products',
                    'magento_url' => '/catalogsearch/result/'
                ],
                [
                    'action' => 'browse_categories', 
                    'label' => 'Browse categories',
                    'magento_url' => '/'
                ],
                [
                    'action' => 'view_cart',
                    'label' => 'View my cart',
                    'magento_url' => '/checkout/cart/'
                ]
            ],
            'product_recommendations' => [],
            'magento_integration' => [
                'ai_powered' => false,
                'fallback_used' => true,
                'nlp_processing' => false,
                'context_aware' => false
            ]
        ];
    }
}