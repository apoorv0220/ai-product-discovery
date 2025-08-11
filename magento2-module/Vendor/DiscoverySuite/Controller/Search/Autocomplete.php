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

use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\App\Action\HttpGetActionInterface;
use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Psr\Log\LoggerInterface;

class Autocomplete implements HttpGetActionInterface, HttpPostActionInterface
{
    /**
     * @var SearchInterface
     */
    private $searchService;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var RequestInterface
     */
    private $request;

    /**
     * @var JsonFactory
     */
    private $resultJsonFactory;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param SearchInterface $searchService
     * @param Data $helper
     * @param RequestInterface $request
     * @param JsonFactory $resultJsonFactory
     * @param LoggerInterface $logger
     */
    public function __construct(
        SearchInterface $searchService,
        Data $helper,
        RequestInterface $request,
        JsonFactory $resultJsonFactory,
        LoggerInterface $logger
    ) {
        $this->searchService = $searchService;
        $this->helper = $helper;
        $this->request = $request;
        $this->resultJsonFactory = $resultJsonFactory;
        $this->logger = $logger;
    }

    /**
     * Execute autocomplete action
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->resultJsonFactory->create();

        if (!$this->helper->isAutocompleteEnabled()) {
            return $result->setData([
                'success' => false,
                'message' => 'Autocomplete is disabled',
                'suggestions' => []
            ]);
        }

        try {
            $query = trim((string) $this->request->getParam('q', ''));
            $limit = (int) $this->request->getParam('limit', 10);

            if (strlen($query) < 2) {
                return $result->setData([
                    'success' => false,
                    'message' => 'Query too short',
                    'suggestions' => []
                ]);
            }

            $suggestions = $this->searchService->autocomplete($query, $limit);

            return $result->setData([
                'success' => true,
                'query' => $query,
                'suggestions' => $suggestions
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Autocomplete request failed', [
                'query' => $this->request->getParam('q', ''),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'success' => false,
                'message' => 'Autocomplete request failed',
                'suggestions' => []
            ]);
        }
    }
}