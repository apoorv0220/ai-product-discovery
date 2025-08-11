<?php
/**
 * DiscoverySuite Search Interface
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Api;

interface SearchInterface
{
    /**
     * Perform search query
     *
     * @param string $query
     * @param int $limit
     * @param int $offset
     * @param array $filters
     * @return array
     */
    public function search(string $query, int $limit = 20, int $offset = 0, array $filters = []): array;

    /**
     * Get autocomplete suggestions
     *
     * @param string $query
     * @param int $limit
     * @return array
     */
    public function autocomplete(string $query, int $limit = 10): array;

    /**
     * Index product data
     *
     * @param array $products
     * @return bool
     */
    public function indexProducts(array $products): bool;

    /**
     * Delete product from index
     *
     * @param int $productId
     * @return bool
     */
    public function deleteProduct(int $productId): bool;
}