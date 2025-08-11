<?php
/**
 * DiscoverySuite Shopping Assistant Interface
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
     * Start chat session
     *
     * @param string $userId
     * @param array $context
     * @return array
     */
    public function startSession(string $userId, array $context = []): array;

    /**
     * Send message to assistant
     *
     * @param string $sessionId
     * @param string $message
     * @param array $context
     * @return array
     */
    public function sendMessage(string $sessionId, string $message, array $context = []): array;

    /**
     * End chat session
     *
     * @param string $sessionId
     * @return bool
     */
    public function endSession(string $sessionId): bool;

    /**
     * Get session history
     *
     * @param string $sessionId
     * @return array
     */
    public function getSessionHistory(string $sessionId): array;
}