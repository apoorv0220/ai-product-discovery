<?php
/**
 * DiscoverySuite Product Delete Observer
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

class ProductDeleteObserver implements ObserverInterface
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
        if (!$this->helper->isEnabled()) {
            return;
        }

        try {
            $product = $observer->getEvent()->getProduct();
            
            if ($product && $product->getId()) {
                $this->logger->info(
                    'DiscoverySuite: Product deleted',
                    [
                        'product_id' => $product->getId(),
                        'sku' => $product->getSku()
                    ]
                );

                // Remove product from search index
                $this->removeProductFromSearchService($product);
            }
        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Error in ProductDeleteObserver',
                ['error' => $e->getMessage()]
            );
        }
    }

    /**
     * Remove product from search service
     *
     * @param \Magento\Catalog\Model\Product $product
     * @return void
     */
    private function removeProductFromSearchService($product)
    {
        // Placeholder implementation
        if ($this->helper->isDebugMode()) {
            $this->logger->debug(
                'DiscoverySuite: Would remove product from search service',
                [
                    'product_id' => $product->getId(),
                    'search_service_url' => $this->helper->getServiceUrl('search', '/api/v1/index/')
                ]
            );
        }
    }
}