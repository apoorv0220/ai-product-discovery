<?php
/**
 * DiscoverySuite Analytics Track Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Controller\Analytics;

use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Vendor\DiscoverySuite\Api\AnalyticsInterface;
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
     * @var AnalyticsInterface
     */
    private $analyticsService;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param RequestInterface $request
     * @param JsonFactory $jsonFactory
     * @param AnalyticsInterface $analyticsService
     * @param LoggerInterface $logger
     */
    public function __construct(
        RequestInterface $request,
        JsonFactory $jsonFactory,
        AnalyticsInterface $analyticsService,
        LoggerInterface $logger
    ) {
        $this->request = $request;
        $this->jsonFactory = $jsonFactory;
        $this->analyticsService = $analyticsService;
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
            // Get request data
            $input = file_get_contents('php://input');
            $data = json_decode($input, true);

            if (!$data) {
                $data = $this->request->getParams();
            }

            $eventType = $data['event_type'] ?? '';
            $eventData = $data['event_data'] ?? [];
            $customerId = isset($data['customer_id']) && $data['customer_id'] ? (int) $data['customer_id'] : null;
            $sessionId = $data['session_id'] ?? null;
            $storeId = isset($data['store_id']) ? (int) $data['store_id'] : null;

            // Validate required fields
            if (empty($eventType)) {
                return $result->setData([
                    'success' => false,
                    'error' => 'Event type is required'
                ]);
            }

            // Track the event
            $success = $this->analyticsService->trackEvent(
                $eventType,
                $eventData,
                $customerId,
                $sessionId,
                $storeId
            );

            return $result->setData([
                'success' => $success,
                'message' => $success ? 'Event tracked successfully' : 'Failed to track event'
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Analytics tracking controller error', [
                'request_data' => $this->request->getParams(),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'success' => false,
                'error' => 'Tracking failed',
                'message' => $e->getMessage()
            ]);
        }
    }
}