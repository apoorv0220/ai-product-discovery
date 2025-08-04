<?php
/**
 * DiscoverySuite Recommendations Track Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Controller\Recommendations;

use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Vendor\DiscoverySuite\Api\RecommendationInterface;
use Psr\Log\LoggerInterface;

class Track implements HttpPostActionInterface
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
     * @var RecommendationInterface
     */
    private $recommendationService;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param RequestInterface $request
     * @param JsonFactory $jsonFactory
     * @param RecommendationInterface $recommendationService
     * @param LoggerInterface $logger
     */
    public function __construct(
        RequestInterface $request,
        JsonFactory $jsonFactory,
        RecommendationInterface $recommendationService,
        LoggerInterface $logger
    ) {
        $this->request = $request;
        $this->jsonFactory = $jsonFactory;
        $this->recommendationService = $recommendationService;
        $this->logger = $logger;
    }

    /**
     * Execute tracking request
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->jsonFactory->create();

        try {
            $recommendationId = $this->request->getParam('recommendation_id');
            $productId = (int) $this->request->getParam('product_id');
            $action = $this->request->getParam('action');
            $position = $this->request->getParam('position') ? (int) $this->request->getParam('position') : null;
            $customerId = $this->request->getParam('customer_id') ? (int) $this->request->getParam('customer_id') : null;

            // Additional metadata
            $metadata = [
                'context' => $this->request->getParam('context'),
                'position' => $position,
                'timestamp' => $this->request->getParam('timestamp'),
                'user_agent' => $this->request->getHeader('User-Agent'),
                'referrer' => $this->request->getHeader('Referer')
            ];

            // Track the interaction
            $success = $this->recommendationService->trackInteraction(
                $recommendationId,
                $productId,
                $action,
                $customerId,
                $metadata
            );

            return $result->setData([
                'success' => $success,
                'message' => $success ? 'Interaction tracked successfully' : 'Failed to track interaction'
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Recommendation tracking error', [
                'recommendation_id' => $this->request->getParam('recommendation_id'),
                'product_id' => $this->request->getParam('product_id'),
                'action' => $this->request->getParam('action'),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'success' => false,
                'message' => 'Tracking failed'
            ]);
        }
    }
}