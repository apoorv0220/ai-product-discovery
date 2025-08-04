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

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Observer;

use Magento\Framework\Event\Observer;
use Magento\Framework\Event\ObserverInterface;
use Vendor\DiscoverySuite\Api\SearchInterface;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;
use Psr\Log\LoggerInterface;

class ProductSaveObserver implements ObserverInterface
{
    /**
     * @var SearchInterface
     */
    private $searchService;

    /**
     * @var ScopeConfigInterface
     */
    private $scopeConfig;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Configuration paths
     */
    const XML_PATH_SEARCH_ENABLED = 'discovery_suite/search/enabled';

    /**
     * @param SearchInterface $searchService
     * @param ScopeConfigInterface $scopeConfig
     * @param LoggerInterface $logger
     */
    public function __construct(
        SearchInterface $searchService,
        ScopeConfigInterface $scopeConfig,
        LoggerInterface $logger
    ) {
        $this->searchService = $searchService;
        $this->scopeConfig = $scopeConfig;
        $this->logger = $logger;
    }

    /**
     * Execute observer
     *
     * @param Observer $observer
     * @return void
     */
    public function execute(Observer $observer): void
    {
        if (!$this->isSearchEnabled()) {
            return;
        }

        try {
            $product = $observer->getEvent()->getProduct();
            
            if (!$product || !$product->getId()) {
                return;
            }

            // Index the product in the AI search service
            $this->searchService->indexProduct((int) $product->getId());

        } catch (\Exception $e) {
            $this->logger->error('Product save observer error', [
                'product_id' => $product ? $product->getId() : 'unknown',
                'error' => $e->getMessage()
            ]);
        }
    }

    /**
     * Check if search is enabled
     *
     * @return bool
     */
    private function isSearchEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_SEARCH_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }
}