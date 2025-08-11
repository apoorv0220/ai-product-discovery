<?php
/**
 * DiscoverySuite Search Service
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Model\Search;

use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Psr\Log\LoggerInterface;

class SearchService implements SearchInterface
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
     * Perform search query
     *
     * @param string $query
     * @param int $limit
     * @param int $offset
     * @param array $filters
     * @return array
     */
    public function search(string $query, int $limit = 20, int $offset = 0, array $filters = []): array
    {
        if (!$this->helper->isSearchEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('search', '/api/v1/search/');
            
            $requestData = [
                'query' => $query,
                'limit' => $limit,
                'offset' => $offset,
                'filters' => $filters
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return $response ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Search API error',
                ['error' => $e->getMessage(), 'query' => $query]
            );
            return [];
        }
    }

    /**
     * Get autocomplete suggestions
     *
     * @param string $query
     * @param int $limit
     * @return array
     */
    public function autocomplete(string $query, int $limit = 10): array
    {
        if (!$this->helper->isAutocompleteEnabled()) {
            return [];
        }

        try {
            $endpoint = $this->helper->getServiceUrl('search', '/api/v1/autocomplete/');
            
            $requestData = [
                'query' => $query,
                'limit' => $limit
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return $response['suggestions'] ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Autocomplete API error',
                ['error' => $e->getMessage(), 'query' => $query]
            );
            return [];
        }
    }

    /**
     * Index product data
     *
     * @param array $products
     * @return bool
     */
    public function indexProducts(array $products): bool
    {
        if (!$this->helper->isEnabled()) {
            return false;
        }

        try {
            $endpoint = $this->helper->getServiceUrl('search', '/api/v1/index/');
            
            $requestData = [
                'products' => $products
            ];

            $response = $this->httpClient->post($endpoint, $requestData);
            
            return isset($response['success']) && $response['success'] === true;

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Product indexing error',
                ['error' => $e->getMessage(), 'product_count' => count($products)]
            );
            return false;
        }
    }

    /**
     * Delete product from index
     *
     * @param int $productId
     * @return bool
     */
    public function deleteProduct(int $productId): bool
    {
        if (!$this->helper->isEnabled()) {
            return false;
        }

        try {
            $endpoint = $this->helper->getServiceUrl('search', "/api/v1/index/{$productId}");
            
            $response = $this->httpClient->delete($endpoint);
            
            return isset($response['success']) && $response['success'] === true;

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Product deletion error',
                ['error' => $e->getMessage(), 'product_id' => $productId]
            );
            return false;
        }
    }
}