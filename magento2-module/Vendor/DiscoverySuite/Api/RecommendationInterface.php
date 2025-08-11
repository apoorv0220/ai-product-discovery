<?php
/**
 * DiscoverySuite Recommendation Interface
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Api;

interface RecommendationInterface
{
    /**
     * Get product recommendations
     *
     * @param string $userId
     * @param string $context
     * @param int $limit
     * @param array $filters
     * @return array
     */
    public function getRecommendations(string $userId, string $context, int $limit = 12, array $filters = []): array;

    /**
     * Get similar products
     *
     * @param int $productId
     * @param int $limit
     * @return array
     */
    public function getSimilarProducts(int $productId, int $limit = 12): array;

    /**
     * Track user interaction
     *
     * @param string $userId
     * @param int $productId
     * @param string $action
     * @param array $context
     * @return bool
     */
    public function trackInteraction(string $userId, int $productId, string $action, array $context = []): bool;
}