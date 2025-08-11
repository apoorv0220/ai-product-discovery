<?php
/**
 * DiscoverySuite Customer Login Observer
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

class CustomerLoginObserver implements ObserverInterface
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
            $customer = $observer->getEvent()->getCustomer();
            
            if ($customer && $customer->getId()) {
                $this->logger->info(
                    'DiscoverySuite: Customer login event',
                    [
                        'customer_id' => $customer->getId(),
                        'email' => $customer->getEmail()
                    ]
                );

                // Track login event for analytics
                $this->trackCustomerLogin($customer);
            }
        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Error in CustomerLoginObserver',
                ['error' => $e->getMessage()]
            );
        }
    }

    /**
     * Track customer login event
     *
     * @param \Magento\Customer\Model\Customer $customer
     * @return void
     */
    private function trackCustomerLogin($customer)
    {
        // Placeholder implementation
        if ($this->helper->isDebugMode()) {
            $this->logger->debug(
                'DiscoverySuite: Would track customer login',
                [
                    'customer_id' => $customer->getId(),
                    'analytics_service_url' => $this->helper->getServiceUrl('analytics', '/api/v1/events/')
                ]
            );
        }
    }
}