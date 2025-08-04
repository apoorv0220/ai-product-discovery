<?php
/**
 * DiscoverySuite Recommendation API Interface
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Api;

interface RecommendationInterface
{
    /**
     * Get personalized product recommendations
     *
     * @param string $context Recommendation context (homepage, product, cart, category)
     * @param array $params Context-specific parameters
     * @param int|null $customerId Customer ID
     * @param int|null $storeId Store ID
     * @param int $limit Number of recommendations
     * @return array Recommended products
     */
    public function getRecommendations(
        string $context,
        array $params = [],
        ?int $customerId = null,
        ?int $storeId = null,
        int $limit = 12
    ): array;

    /**
     * Get cross-sell recommendations for product
     *
     * @param int $productId Product ID
     * @param int|null $customerId Customer ID
     * @param int|null $storeId Store ID
     * @param int $limit Number of recommendations
     * @return array Cross-sell products
     */
    public function getCrossSellRecommendations(
        int $productId,
        ?int $customerId = null,
        ?int $storeId = null,
        int $limit = 6
    ): array;

    /**
     * Get up-sell recommendations for product
     *
     * @param int $productId Product ID
     * @param int|null $customerId Customer ID
     * @param int|null $storeId Store ID
     * @param int $limit Number of recommendations
     * @return array Up-sell products
     */
    public function getUpSellRecommendations(
        int $productId,
        ?int $customerId = null,
        ?int $storeId = null,
        int $limit = 6
    ): array;

    /**
     * Get similar products
     *
     * @param int $productId Product ID
     * @param int|null $storeId Store ID
     * @param int $limit Number of recommendations
     * @return array Similar products
     */
    public function getSimilarProducts(
        int $productId,
        ?int $storeId = null,
        int $limit = 8
    ): array;

    /**
     * Get trending/popular products
     *
     * @param string $period Time period (day, week, month)
     * @param int|null $categoryId Category ID
     * @param int|null $storeId Store ID
     * @param int $limit Number of recommendations
     * @return array Trending products
     */
    public function getTrendingProducts(
        string $period = 'week',
        ?int $categoryId = null,
        ?int $storeId = null,
        int $limit = 12
    ): array;

    /**
     * Get cart-based recommendations
     *
     * @param array $cartProductIds Product IDs in cart
     * @param int|null $customerId Customer ID
     * @param int|null $storeId Store ID
     * @param int $limit Number of recommendations
     * @return array Cart-based recommendations
     */
    public function getCartRecommendations(
        array $cartProductIds,
        ?int $customerId = null,
        ?int $storeId = null,
        int $limit = 8
    ): array;

    /**
     * Track recommendation interaction
     *
     * @param string $recommendationId Recommendation ID
     * @param int $productId Product ID
     * @param string $action Action type (view, click, add_to_cart, purchase)
     * @param int|null $customerId Customer ID
     * @param array $metadata Additional metadata
     * @return bool Success status
     */
    public function trackInteraction(
        string $recommendationId,
        int $productId,
        string $action,
        ?int $customerId = null,
        array $metadata = []
    ): bool;

    /**
     * Get recommendation performance analytics
     *
     * @param string $period Time period
     * @param string|null $context Recommendation context
     * @param int|null $storeId Store ID
     * @return array Analytics data
     */
    public function getRecommendationAnalytics(
        string $period = 'week',
        ?string $context = null,
        ?int $storeId = null
    ): array;

    /**
     * Update user behavior profile
     *
     * @param int|null $customerId Customer ID
     * @param string $sessionId Session ID
     * @param array $behaviorData Behavior data
     * @return bool Success status
     */
    public function updateUserProfile(
        ?int $customerId,
        string $sessionId,
        array $behaviorData
    ): bool;
}