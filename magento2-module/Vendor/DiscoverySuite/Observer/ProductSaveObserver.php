<?php
/**
 * DiscoverySuite Product Save Observer
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

class ProductSaveObserver implements ObserverInterface
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
                // Log the product save event
                $this->logger->info(
                    'DiscoverySuite: Product saved',
                    [
                        'product_id' => $product->getId(),
                        'sku' => $product->getSku(),
                        'name' => $product->getName()
                    ]
                );

                // Here you would typically:
                // 1. Format the product data for the AI service
                // 2. Send the product to the search indexing service
                // 3. Trigger recommendation model updates if needed
                
                // Placeholder for actual implementation
                $this->syncProductToSearchService($product);
            }
        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Error in ProductSaveObserver',
                ['error' => $e->getMessage()]
            );
        }
    }

    /**
     * Sync product to search service
     *
     * @param \Magento\Catalog\Model\Product $product
     * @return void
     */
    private function syncProductToSearchService($product)
    {
        // Placeholder implementation
        // In a real implementation, you would:
        // 1. Format product data according to your AI service requirements
        // 2. Call the search service API to index the product
        // 3. Handle any errors and implement retry logic
        
        if ($this->helper->isDebugMode()) {
            $this->logger->debug(
                'DiscoverySuite: Would sync product to search service',
                [
                    'product_id' => $product->getId(),
                    'search_service_url' => $this->helper->getServiceUrl('search', '/api/v1/index/')
                ]
            );
        }
    }
}