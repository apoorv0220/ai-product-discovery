<?php
/**
 * DiscoverySuite Search Controller
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

class Index implements HttpGetActionInterface
{
    /**
     * @var JsonFactory
     */
    private $jsonFactory;

    /**
     * @var SearchInterface
     */
    private $searchService;

    /**
     * @var RequestInterface
     */
    private $request;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param JsonFactory $jsonFactory
     * @param SearchInterface $searchService
     * @param RequestInterface $request
     * @param LoggerInterface $logger
     */
    public function __construct(
        JsonFactory $jsonFactory,
        SearchInterface $searchService,
        RequestInterface $request,
        LoggerInterface $logger
    ) {
        $this->jsonFactory = $jsonFactory;
        $this->searchService = $searchService;
        $this->request = $request;
        $this->logger = $logger;
    }

    /**
     * Execute search action
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->jsonFactory->create();

        try {
            $query = $this->request->getParam('q', '');
            $limit = (int) $this->request->getParam('limit', 20);
            $offset = (int) $this->request->getParam('offset', 0);
            
            if (empty($query)) {
                return $result->setData([
                    'error' => true,
                    'message' => 'Search query is required'
                ]);
            }

            $searchResults = $this->searchService->search($query, null, [], $limit, $offset);

            return $result->setData([
                'success' => true,
                'results' => $searchResults['results'] ?? [],
                'total' => $searchResults['total'] ?? 0,
                'took' => $searchResults['took'] ?? 0,
                'query' => $query
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Search controller error: ' . $e->getMessage());
            
            return $result->setData([
                'error' => true,
                'message' => 'Search service unavailable'
            ]);
        }
    }
}