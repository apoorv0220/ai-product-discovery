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

use Vendor\DiscoverySuite\Api\AnalyticsInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Magento\Customer\Model\Session as CustomerSession;
use Psr\Log\LoggerInterface;

class Track implements HttpPostActionInterface
{
    /**
     * @var AnalyticsInterface
     */
    private $analyticsService;

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
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param AnalyticsInterface $analyticsService
     * @param Data $helper
     * @param RequestInterface $request
     * @param JsonFactory $resultJsonFactory
     * @param CustomerSession $customerSession
     * @param LoggerInterface $logger
     */
    public function __construct(
        AnalyticsInterface $analyticsService,
        Data $helper,
        RequestInterface $request,
        JsonFactory $resultJsonFactory,
        CustomerSession $customerSession,
        LoggerInterface $logger
    ) {
        $this->analyticsService = $analyticsService;
        $this->helper = $helper;
        $this->request = $request;
        $this->resultJsonFactory = $resultJsonFactory;
        $this->customerSession = $customerSession;
        $this->logger = $logger;
    }

    /**
     * Execute track analytics event action
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->resultJsonFactory->create();

        if (!$this->helper->isAnalyticsEnabled()) {
            return $result->setData([
                'success' => false,
                'message' => 'Analytics tracking is disabled'
            ]);
        }

        try {
            $eventType = (string) $this->request->getParam('event_type');
            $eventData = $this->request->getParam('event_data', []);

            if (!$eventType) {
                return $result->setData([
                    'success' => false,
                    'message' => 'Missing event type'
                ]);
            }

            $userId = $this->getUserId();

            // Sanitize and validate event data
            if (!is_array($eventData)) {
                $eventData = [];
            }

            // Add standard tracking data
            $eventData['timestamp'] = time();
            $eventData['user_agent'] = $this->request->getServer('HTTP_USER_AGENT');
            $eventData['ip_address'] = $this->request->getClientIp();
            $eventData['referrer'] = $this->request->getServer('HTTP_REFERER');

            $tracked = $this->analyticsService->trackEvent(
                $eventType,
                $eventData,
                $userId
            );

            if ($tracked) {
                return $result->setData([
                    'success' => true,
                    'message' => 'Event tracked successfully'
                ]);
            } else {
                return $result->setData([
                    'success' => false,
                    'message' => 'Failed to track event'
                ]);
            }

        } catch (\Exception $e) {
            $this->logger->error('Analytics tracking failed', [
                'event_type' => $this->request->getParam('event_type'),
                'user_id' => $this->getUserId(),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'success' => false,
                'message' => 'Analytics tracking failed'
            ]);
        }
    }

    /**
     * Get user ID
     *
     * @return string
     */
    private function getUserId(): string
    {
        if ($this->customerSession->isLoggedIn()) {
            return 'customer_' . $this->customerSession->getCustomerId();
        }

        return 'guest_' . $this->customerSession->getSessionId();
    }
}