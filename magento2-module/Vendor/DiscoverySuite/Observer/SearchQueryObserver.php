<?php
/**
 * DiscoverySuite Search Query Observer
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

class SearchQueryObserver implements ObserverInterface
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
            $query = $observer->getEvent()->getQuery();
            
            if ($query && $query->getQueryText()) {
                $this->logger->info(
                    'DiscoverySuite: Search query performed',
                    [
                        'query_text' => $query->getQueryText(),
                        'num_results' => $query->getNumResults(),
                        'popularity' => $query->getPopularity()
                    ]
                );

                // Track search query for analytics
                $this->trackSearchQuery($query);
            }
        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite: Error in SearchQueryObserver',
                ['error' => $e->getMessage()]
            );
        }
    }

    /**
     * Track search query event
     *
     * @param \Magento\Search\Model\Query $query
     * @return void
     */
    private function trackSearchQuery($query)
    {
        // Placeholder implementation
        if ($this->helper->isDebugMode()) {
            $this->logger->debug(
                'DiscoverySuite: Would track search query',
                [
                    'query_text' => $query->getQueryText(),
                    'analytics_service_url' => $this->helper->getServiceUrl('analytics', '/api/v1/events/')
                ]
            );
        }
    }
}