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
    public function search(string $query, int $limit = 20, int $offset = 0, array $filters = [], string $userId = null): array
    {
        if (!$this->helper->isSearchEnabled()) {
            return [];
        }

        // Check if AI service is available
        if (!$this->helper->isServiceAvailable('search')) {
            $this->logger->warning('Search service unavailable', ['query' => $query]);
            return [
                'results' => [],
                'total' => 0,
                'query' => $query,
                'error' => 'AI search service is currently unavailable',
                'fallback_mode' => true
            ];
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
            
            // Process advanced AI response
            if ($response && isset($response['results'])) {
                // Extract NLP insights if available
                $nlpInsights = $response['search_metadata'] ?? [];
                
                // Add AI enhancement metadata to each result (only if provided by AI service)
                foreach ($response['results'] as &$result) {
                    if (isset($nlpInsights['nlp_enabled'])) {
                        $result['nlp_enabled'] = $nlpInsights['nlp_enabled'];
                    }
                    if (isset($nlpInsights['semantic_search'])) {
                        $result['semantic_search'] = $nlpInsights['semantic_search'];
                    }
                    if (isset($nlpInsights['typo_corrected'])) {
                        $result['typo_corrected'] = $nlpInsights['typo_corrected'];
                    }
                    $result['ai_enhanced'] = !empty($nlpInsights);
                }
                
                // Preserve original search_metadata from AI service
                if (!isset($response['search_metadata'])) {
                    $response['search_metadata'] = $nlpInsights;
                }
                
                // Add user-friendly AI messages
                if (!empty($nlpInsights['corrections'])) {
                    $correction = $nlpInsights['corrections'][0] ?? [];
                    if (isset($correction['original']) && isset($correction['corrected'])) {
                        $response['ai_message'] = sprintf(
                            'Showing results for "%s" instead of "%s"',
                            $correction['corrected'],
                            $correction['original']
                        );
                    }
                }
                
                if (!empty($nlpInsights['intent']['type'])) {
                    $intentMessages = [
                        'buy' => 'Found products you can purchase right now',
                        'compare' => 'Here are products to compare',
                        'browse' => 'Showing products to browse'
                    ];
                    
                    $intent = $nlpInsights['intent']['type'];
                    if (isset($intentMessages[$intent])) {
                        $response['intent_message'] = $intentMessages[$intent];
                    }
                }
            }
            
            return $response ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Search API error',
                ['error' => $e->getMessage(), 'query' => $query]
            );
            return [
                'results' => [],
                'total' => 0,
                'query' => $query,
                'error' => 'Search request failed: ' . $e->getMessage(),
                'ai_enhanced' => false
            ];
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
            
            // Use GET request with query parameters (as per your API)
            $response = $this->httpClient->get($endpoint, [
                'q' => $query,
                'limit' => $limit
            ]);
            
            // Process NLP-enhanced autocomplete response
            if ($response && isset($response['suggestions'])) {
                $metadata = $response['autocomplete_metadata'] ?? [];
                
                // Add AI enhancement flags to suggestions
                foreach ($response['suggestions'] as &$suggestion) {
                    $suggestion['ai_enhanced'] = $suggestion['nlp_enhanced'] ?? false;
                    $suggestion['has_typo_correction'] = $suggestion['is_corrected'] ?? false;
                    
                    // Add user-friendly indicators
                    if ($suggestion['has_typo_correction']) {
                        $suggestion['correction_note'] = sprintf(
                            'Did you mean "%s"?',
                            $suggestion['suggestion']
                        );
                    }
                }
                
                // Add metadata about AI processing (only if metadata exists)
                if (!empty($metadata)) {
                    $response['ai_metadata'] = [
                        'nlp_processing' => $metadata['nlp_processing'] ?? false,
                        'typo_corrections' => $this->countTypoCorrections($response['suggestions']),
                        'intent_detection' => $metadata['intent_detection'] ?? false,
                        'semantic_search' => $metadata['semantic_search'] ?? false,
                        'ai_enhanced' => true
                    ];
                }
                
                return $response;
            }
            
            return $response['suggestions'] ?? [];

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Autocomplete API error',
                ['error' => $e->getMessage(), 'query' => $query]
            );
            return [
                'suggestions' => [],
                'query' => $query,
                'error' => 'Autocomplete request failed: ' . $e->getMessage(),
                'ai_enhanced' => false
            ];
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
            $endpoint = $this->helper->getServiceUrl('search', '/api/v1/index/products');
            
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
    
    /**
     * Count typo corrections in suggestions
     *
     * @param array $suggestions
     * @return int
     */
    private function countTypoCorrections(array $suggestions): int
    {
        $count = 0;
        foreach ($suggestions as $suggestion) {
            if (isset($suggestion['is_corrected']) && $suggestion['is_corrected']) {
                $count++;
            }
        }
        return $count;
    }
}