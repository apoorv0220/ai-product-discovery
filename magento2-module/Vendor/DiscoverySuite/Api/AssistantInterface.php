<?php
/**
 * DiscoverySuite Shopping Assistant API Interface
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Api;

interface AssistantInterface
{
    /**
     * Start a new shopping session
     *
     * @param array $userContext User context data
     * @param int|null $customerId Customer ID
     * @param int|null $storeId Store ID
     * @return array Session data
     */
    public function startSession(
        array $userContext = [],
        ?int $customerId = null,
        ?int $storeId = null
    ): array;

    /**
     * Process user input and get assistant response
     *
     * @param string $sessionId Session ID
     * @param string $userInput User input/message
     * @param array $context Additional context
     * @return array Assistant response
     */
    public function processInput(
        string $sessionId,
        string $userInput,
        array $context = []
    ): array;

    /**
     * Get guided flow questions
     *
     * @param string $flowType Flow type (category selection, product finder, etc.)
     * @param array $currentAnswers Current answers
     * @param int|null $storeId Store ID
     * @return array Flow questions
     */
    public function getGuidedFlow(
        string $flowType,
        array $currentAnswers = [],
        ?int $storeId = null
    ): array;

    /**
     * Submit guided flow answers and get recommendations
     *
     * @param string $flowType Flow type
     * @param array $answers User answers
     * @param int|null $customerId Customer ID
     * @param int|null $storeId Store ID
     * @return array Product recommendations
     */
    public function submitGuidedFlow(
        string $flowType,
        array $answers,
        ?int $customerId = null,
        ?int $storeId = null
    ): array;

    /**
     * Get product recommendations based on requirements
     *
     * @param array $requirements User requirements
     * @param array $preferences User preferences
     * @param int|null $customerId Customer ID
     * @param int|null $storeId Store ID
     * @param int $limit Number of recommendations
     * @return array Product recommendations
     */
    public function getProductRecommendations(
        array $requirements,
        array $preferences = [],
        ?int $customerId = null,
        ?int $storeId = null,
        int $limit = 10
    ): array;

    /**
     * Compare products
     *
     * @param array $productIds Product IDs to compare
     * @param array $comparisonCriteria Comparison criteria
     * @param int|null $storeId Store ID
     * @return array Product comparison data
     */
    public function compareProducts(
        array $productIds,
        array $comparisonCriteria = [],
        ?int $storeId = null
    ): array;

    /**
     * Get assistant analytics
     *
     * @param string $period Time period
     * @param int|null $storeId Store ID
     * @return array Analytics data
     */
    public function getAssistantAnalytics(
        string $period = 'week',
        ?int $storeId = null
    ): array;

    /**
     * Track assistant interaction
     *
     * @param string $sessionId Session ID
     * @param string $interactionType Interaction type
     * @param array $interactionData Interaction data
     * @param int|null $customerId Customer ID
     * @return bool Success status
     */
    public function trackInteraction(
        string $sessionId,
        string $interactionType,
        array $interactionData,
        ?int $customerId = null
    ): bool;

    /**
     * End shopping session
     *
     * @param string $sessionId Session ID
     * @param array $sessionSummary Session summary data
     * @return bool Success status
     */
    public function endSession(
        string $sessionId,
        array $sessionSummary = []
    ): bool;

    /**
     * Get session history
     *
     * @param string $sessionId Session ID
     * @return array Session history
     */
    public function getSessionHistory(string $sessionId): array;

    /**
     * Get available assistant flows
     *
     * @param int|null $storeId Store ID
     * @return array Available flows
     */
    public function getAvailableFlows(?int $storeId = null): array;

    /**
     * Create custom flow
     *
     * @param string $flowName Flow name
     * @param array $flowConfig Flow configuration
     * @param int|null $storeId Store ID
     * @return string Flow ID
     */
    public function createCustomFlow(
        string $flowName,
        array $flowConfig,
        ?int $storeId = null
    ): string;
}