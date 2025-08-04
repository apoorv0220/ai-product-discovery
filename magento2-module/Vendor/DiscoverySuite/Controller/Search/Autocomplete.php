<?php
/**
 * DiscoverySuite Search Autocomplete Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Controller\Search;

use Magento\Framework\App\Action\HttpGetActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Vendor\DiscoverySuite\Api\SearchInterface;
use Psr\Log\LoggerInterface;

class Autocomplete implements HttpGetActionInterface
{
    /**
     * @var RequestInterface
     */
    private $request;

    /**
     * @var JsonFactory
     */
    private $jsonFactory;

    /**
     * @var SearchInterface
     */
    private $searchService;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param RequestInterface $request
     * @param JsonFactory $jsonFactory
     * @param SearchInterface $searchService
     * @param LoggerInterface $logger
     */
    public function __construct(
        RequestInterface $request,
        JsonFactory $jsonFactory,
        SearchInterface $searchService,
        LoggerInterface $logger
    ) {
        $this->request = $request;
        $this->jsonFactory = $jsonFactory;
        $this->searchService = $searchService;
        $this->logger = $logger;
    }

    /**
     * Execute autocomplete request
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->jsonFactory->create();

        try {
            $query = trim((string) $this->request->getParam('q', ''));
            $limit = (int) $this->request->getParam('limit', 10);

            if (empty($query)) {
                return $result->setData([
                    'suggestions' => [],
                    'products' => [],
                    'categories' => []
                ]);
            }

            // Get autocomplete results from AI service
            $autocompleteData = $this->searchService->autocomplete($query, null, $limit);

            // Get spell corrections and suggestions
            $suggestions = $this->searchService->getSuggestions($query);

            // Merge the data
            $responseData = [
                'suggestions' => $autocompleteData['suggestions'] ?? [],
                'products' => $autocompleteData['products'] ?? [],
                'categories' => $autocompleteData['categories'] ?? [],
                'spell_correction' => $suggestions['spell_correction'] ?? null,
                'related_queries' => $suggestions['related_queries'] ?? []
            ];

            return $result->setData($responseData);

        } catch (\Exception $e) {
            $this->logger->error('Autocomplete controller error', [
                'query' => $this->request->getParam('q', ''),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'suggestions' => [],
                'products' => [],
                'categories' => [],
                'error' => 'Autocomplete service temporarily unavailable'
            ]);
        }
    }
}