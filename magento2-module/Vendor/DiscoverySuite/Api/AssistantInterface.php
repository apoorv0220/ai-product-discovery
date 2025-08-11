<?php
/**
 * DiscoverySuite Assistant Interface
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Api;

interface AssistantInterface
{
    /**
     * Send message to conversational AI assistant
     *
     * @param string $message
     * @param string $sessionId
     * @param string|null $userId
     * @param array $contextData
     * @return array
     */
    public function chat(string $message, string $sessionId, ?string $userId = null, array $contextData = []): array;

    /**
     * Record user interaction for ML learning
     *
     * @param string $userId
     * @param string $productId
     * @param string $interactionType
     * @param array $context
     * @return bool
     */
    public function recordInteraction(string $userId, string $productId, string $interactionType, array $context = []): bool;

    /**
     * Get conversation history
     *
     * @param string $sessionId
     * @param string|null $userId
     * @return array
     */
    public function getConversationHistory(string $sessionId, ?string $userId = null): array;

    /**
     * Clear conversation session
     *
     * @param string $sessionId
     * @return bool
     */
    public function clearSession(string $sessionId): bool;
}