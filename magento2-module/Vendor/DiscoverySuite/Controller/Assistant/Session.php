<?php
/**
 * AI Product Discovery Suite - Assistant Session Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Controller\Assistant;

use Magento\Framework\App\Action\Action;
use Magento\Framework\App\Action\Context;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\App\Action\HttpGetActionInterface;
use Magento\Framework\App\Action\HttpPostActionInterface;
use Vendor\DiscoverySuite\Helper\Data as DiscoveryHelper;
use Psr\Log\LoggerInterface;

class Session extends Action implements HttpGetActionInterface, HttpPostActionInterface
{
    /**
     * @var JsonFactory
     */
    protected $jsonFactory;

    /**
     * @var DiscoveryHelper
     */
    protected $discoveryHelper;

    /**
     * @var LoggerInterface
     */
    protected $logger;

    /**
     * @param Context $context
     * @param JsonFactory $jsonFactory
     * @param DiscoveryHelper $discoveryHelper
     * @param LoggerInterface $logger
     */
    public function __construct(
        Context $context,
        JsonFactory $jsonFactory,
        DiscoveryHelper $discoveryHelper,
        LoggerInterface $logger
    ) {
        parent::__construct($context);
        $this->jsonFactory = $jsonFactory;
        $this->discoveryHelper = $discoveryHelper;
        $this->logger = $logger;
    }

    /**
     * Execute action
     *
     * @return \Magento\Framework\Controller\Result\Json
     */
    public function execute()
    {
        $result = $this->jsonFactory->create();

        try {
            // Check if the module is enabled
            if (!$this->discoveryHelper->isEnabled()) {
                return $result->setData([
                    'success' => false,
                    'error' => 'AI Discovery Suite is not enabled'
                ]);
            }

            $request = $this->getRequest();
            
            if ($request->isPost()) {
                // Handle chat message
                return $this->handleChatMessage($result);
            } else {
                // Handle session initialization
                return $this->initializeSession($result);
            }

        } catch (\Exception $e) {
            $this->logger->error('Discovery Assistant Session Error: ' . $e->getMessage());
            return $result->setData([
                'success' => false,
                'error' => 'Assistant session failed: ' . $e->getMessage()
            ]);
        }
    }

    /**
     * Initialize chat session
     *
     * @param \Magento\Framework\Controller\Result\Json $result
     * @return \Magento\Framework\Controller\Result\Json
     */
    private function initializeSession($result)
    {
        try {
            // Generate a unique session ID
            $sessionId = uniqid('discovery_chat_', true);
            
            // Get assistant service URL
            $assistantUrl = $this->discoveryHelper->getServiceUrl('shopping_assistant', '/api/v1/chat/session');
            
            // Initialize session with backend
            $client = new \Magento\Framework\HTTP\Client\Curl();
            $client->setHeaders([
                'Content-Type' => 'application/json',
                'User-Agent' => 'Magento-DiscoverySuite/1.0'
            ]);
            
            $requestData = [
                'session_id' => $sessionId,
                'user_context' => [
                    'store_id' => $this->discoveryHelper->getStoreId(),
                    'customer_group' => 'general',
                    'platform' => 'magento2'
                ]
            ];
            
            $client->post($assistantUrl, json_encode($requestData));
            $response = $client->getBody();
            $responseData = json_decode($response, true);

            if (isset($responseData['success']) && $responseData['success']) {
                return $result->setData([
                    'success' => true,
                    'session_id' => $sessionId,
                    'welcome_message' => 'Hello! I\'m your AI shopping assistant. How can I help you find the perfect products today?',
                    'capabilities' => [
                        'product_search',
                        'recommendations',
                        'price_comparison',
                        'feature_explanation'
                    ]
                ]);
            } else {
                // Fallback response if backend is not available
                return $result->setData([
                    'success' => true,
                    'session_id' => $sessionId,
                    'welcome_message' => 'Hello! I\'m your AI shopping assistant. How can I help you today?',
                    'fallback_mode' => true
                ]);
            }

        } catch (\Exception $e) {
            $this->logger->error('Assistant Session Init Error: ' . $e->getMessage());
            
            // Fallback response
            return $result->setData([
                'success' => true,
                'session_id' => uniqid('fallback_', true),
                'welcome_message' => 'Hello! I\'m here to help you find products. What are you looking for?',
                'fallback_mode' => true
            ]);
        }
    }

    /**
     * Handle chat message
     *
     * @param \Magento\Framework\Controller\Result\Json $result
     * @return \Magento\Framework\Controller\Result\Json
     */
    private function handleChatMessage($result)
    {
        try {
            $request = $this->getRequest();
            $message = $request->getParam('message', '');
            $sessionId = $request->getParam('session_id', '');

            if (empty($message)) {
                return $result->setData([
                    'success' => false,
                    'error' => 'Message is required'
                ]);
            }

            // Get assistant service URL
            $assistantUrl = $this->discoveryHelper->getServiceUrl('shopping_assistant', '/api/v1/chat/message');
            
            // Send message to backend
            $client = new \Magento\Framework\HTTP\Client\Curl();
            $client->setHeaders([
                'Content-Type' => 'application/json',
                'User-Agent' => 'Magento-DiscoverySuite/1.0'
            ]);
            
            $requestData = [
                'session_id' => $sessionId,
                'message' => $message,
                'context' => [
                    'store_id' => $this->discoveryHelper->getStoreId(),
                    'timestamp' => date('c')
                ]
            ];
            
            $client->post($assistantUrl, json_encode($requestData));
            $response = $client->getBody();
            $responseData = json_decode($response, true);

            if (isset($responseData['response'])) {
                return $result->setData([
                    'success' => true,
                    'response' => $responseData['response'],
                    'suggestions' => $responseData['suggestions'] ?? [],
                    'products' => $responseData['products'] ?? []
                ]);
            } else {
                // Fallback response
                return $result->setData([
                    'success' => true,
                    'response' => 'I understand you\'re looking for "' . $message . '". Let me help you find the best products!',
                    'fallback_mode' => true
                ]);
            }

        } catch (\Exception $e) {
            $this->logger->error('Assistant Chat Error: ' . $e->getMessage());
            
            return $result->setData([
                'success' => true,
                'response' => 'I\'m here to help! Could you tell me more about what you\'re looking for?',
                'fallback_mode' => true
            ]);
        }
    }
}
