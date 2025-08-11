<?php
/**
 * DiscoverySuite Shopping Assistant Service
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
     * Start chat session
     *
     * @param string $userId
     * @param array $context
     * @return array
     */
    public function startSession(string $userId, array $context = []): array
    {
        if (!$this->helper->isEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('shopping_assistant', '/api/v1/sessions/');
            
            $requestData = [
                'user_id' => $userId,
                'context' => $context
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return $response ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Session start error',
                ['error' => $e->getMessage(), 'user_id' => $userId]
            );
            return [];
        }
    }

    /**
     * Send message to assistant
     *
     * @param string $sessionId
     * @param string $message
     * @param array $context
     * @return array
     */
    public function sendMessage(string $sessionId, string $message, array $context = []): array
    {
        if (!$this->helper->isEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('shopping_assistant', '/api/v1/chat/');
            
            $requestData = [
                'session_id' => $sessionId,
                'message' => $message,
                'context' => $context
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return $response ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Send message error',
                ['error' => $e->getMessage(), 'session_id' => $sessionId]
            );
            return [];
        }
    }

    /**
     * End chat session
     *
     * @param string $sessionId
     * @return bool
     */
    public function endSession(string $sessionId): bool
    {
        if (!$this->helper->isEnabled()) {
            return false;
        }

        try {
            $endpoint = $this->helper->getServiceUrl('shopping_assistant', "/api/v1/sessions/{$sessionId}");
            
            $response = $this->httpClient->delete($endpoint);
            
            return isset($response['success']) && $response['success'] === true;

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: End session error',
                ['error' => $e->getMessage(), 'session_id' => $sessionId]
            );
            return false;
        }
    }

    /**
     * Get session history
     *
     * @param string $sessionId
     * @return array
     */
    public function getSessionHistory(string $sessionId): array
    {
        if (!$this->helper->isEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('shopping_assistant', "/api/v1/sessions/{$sessionId}/history");
            
            $response = $this->httpClient->get($endpoint);
            
            return $response['history'] ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Session history error',
                ['error' => $e->getMessage(), 'session_id' => $sessionId]
            );
            return [];
        }
    }
}