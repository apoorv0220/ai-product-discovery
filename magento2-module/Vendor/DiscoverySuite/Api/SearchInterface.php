<?php
/**
 * DiscoverySuite Search API Interface
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Api;

interface SearchInterface
{
    /**
     * Perform AI-powered product search
     *
     * @param string $query Search query
     * @param int|null $storeId Store ID
     * @param array $filters Additional filters
     * @param int $limit Result limit
     * @param int $offset Result offset
     * @return array Search results
     */
    public function search(
        string $query,
        ?int $storeId = null,
        array $filters = [],
        int $limit = 20,
        int $offset = 0
    ): array;

    /**
     * Get autocomplete suggestions
     *
     * @param string $query Partial query
     * @param int|null $storeId Store ID
     * @param int $limit Number of suggestions
     * @return array Autocomplete suggestions
     */
    public function autocomplete(
        string $query,
        ?int $storeId = null,
        int $limit = 10
    ): array;

    /**
     * Get search suggestions and spell corrections
     *
     * @param string $query Search query
     * @param int|null $storeId Store ID
     * @return array Suggestions array
     */
    public function getSuggestions(
        string $query,
        ?int $storeId = null
    ): array;

    /**
     * Index product for search
     *
     * @param int $productId Product ID
     * @param int|null $storeId Store ID
     * @return bool Success status
     */
    public function indexProduct(int $productId, ?int $storeId = null): bool;

    /**
     * Bulk index products
     *
     * @param array $productIds Array of product IDs
     * @param int|null $storeId Store ID
     * @return bool Success status
     */
    public function bulkIndexProducts(array $productIds, ?int $storeId = null): bool;

    /**
     * Remove product from search index
     *
     * @param int $productId Product ID
     * @param int|null $storeId Store ID
     * @return bool Success status
     */
    public function removeFromIndex(int $productId, ?int $storeId = null): bool;

    /**
     * Rebuild entire search index
     *
     * @param int|null $storeId Store ID
     * @return bool Success status
     */
    public function rebuildIndex(?int $storeId = null): bool;

    /**
     * Get search analytics data
     *
     * @param string $period Time period (day, week, month)
     * @param int|null $storeId Store ID
     * @return array Analytics data
     */
    public function getSearchAnalytics(string $period = 'week', ?int $storeId = null): array;

    /**
     * Track search event
     *
     * @param string $query Search query
     * @param int $resultCount Number of results
     * @param string|null $userId User ID
     * @param array $metadata Additional metadata
     * @return bool Success status
     */
    public function trackSearchEvent(
        string $query,
        int $resultCount,
        ?string $userId = null,
        array $metadata = []
    ): bool;
}