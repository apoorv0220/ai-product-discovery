<?php
/**
 * DiscoverySuite Cart Add Observer
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

class CartAddObserver implements ObserverInterface
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
            $quoteItem = $observer->getEvent()->getQuoteItem();
            
            if ($quoteItem && $quoteItem->getProduct()) {
                $product = $quoteItem->getProduct();
                
                $this->logger->info(
                    'DiscoverySuite: Product added to cart',
                    [
                        'product_id' => $product->getId(),
                        'sku' => $product->getSku(),
                        'qty' => $quoteItem->getQty()
                    ]
                );

                // Track cart addition for analytics
                $this->trackCartAdd($quoteItem);
            }
        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Error in CartAddObserver',
                ['error' => $e->getMessage()]
            );
        }
    }

    /**
     * Track cart addition event
     *
     * @param \Magento\Quote\Model\Quote\Item $quoteItem
     * @return void
     */
    private function trackCartAdd($quoteItem)
    {
        // Placeholder implementation
        if ($this->helper->isDebugMode()) {
            $this->logger->debug(
                'DiscoverySuite: Would track cart addition',
                [
                    'product_id' => $quoteItem->getProduct()->getId(),
                    'analytics_service_url' => $this->helper->getServiceUrl('analytics', '/api/v1/events/')
                ]
            );
        }
    }
}