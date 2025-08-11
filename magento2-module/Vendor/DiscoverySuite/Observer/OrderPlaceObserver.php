<?php
/**
 * DiscoverySuite Order Place Observer
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Observer;

use Magento\Framework\Event\Observer;
use Magento\Framework\Event\ObserverInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Psr\Log\LoggerInterface;

class OrderPlaceObserver implements ObserverInterface
{
    /**
     * @var Data
     */
    private $helper;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param Data $helper
     * @param LoggerInterface $logger
     */
    public function __construct(
        Data $helper,
        LoggerInterface $logger
    ) {
        $this->helper = $helper;
        $this->logger = $logger;
    }

    /**
     * Execute observer
     *
     * @param Observer $observer
     * @return void
     */
    public function execute(Observer $observer)
    {
        if (!$this->helper->isAnalyticsEnabled()) {
            return;
        }

        try {
            $order = $observer->getEvent()->getOrder();
            
            if ($order && $order->getId()) {
                $this->logger->info(
                    'DiscoverySuite: Order placed event',
                    [
                        'order_id' => $order->getId(),
                        'increment_id' => $order->getIncrementId(),
                        'total' => $order->getGrandTotal()
                    ]
                );

                // Track order for analytics and recommendations
                $this->trackOrderPlace($order);
            }
        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Error in OrderPlaceObserver',
                ['error' => $e->getMessage()]
            );
        }
    }

    /**
     * Track order placement event
     *
     * @param \Magento\Sales\Model\Order $order
     * @return void
     */
    private function trackOrderPlace($order)
    {
        // Placeholder implementation
        if ($this->helper->isDebugMode()) {
            $this->logger->debug(
                'DiscoverySuite: Would track order placement',
                [
                    'order_id' => $order->getId(),
                    'analytics_service_url' => $this->helper->getServiceUrl('analytics', '/api/v1/events/'),
                    'recommendation_service_url' => $this->helper->getServiceUrl('recommendation', '/api/v1/train/')
                ]
            );
        }
    }
}