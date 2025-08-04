<?php
/**
 * DiscoverySuite Search Collection Plugin
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Plugin\Search;

use Magento\CatalogSearch\Model\ResourceModel\Fulltext\Collection;
use Vendor\DiscoverySuite\Api\SearchInterface;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;
use Psr\Log\LoggerInterface;

class CollectionPlugin
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
     * Intercept search collection and apply AI ranking
     *
     * @param Collection $subject
     * @param callable $proceed
     * @param string $query
     * @return Collection
     */
    public function aroundAddSearchFilter(Collection $subject, callable $proceed, $query)
    {
        if (!$this->isSearchEnabled()) {
            return $proceed($query);
        }

        try {
            // Get AI search results
            $searchResults = $this->searchService->search($query);
            
            if (!empty($searchResults['products'])) {
                // Extract product IDs from AI results
                $productIds = array_column($searchResults['products'], 'id');
                
                if (!empty($productIds)) {
                    // Apply AI ranking by filtering and ordering collection
                    $subject->addFieldToFilter('entity_id', ['in' => $productIds]);
                    
                    // Apply custom order based on AI ranking
                    $this->applyAIRanking($subject, $productIds);
                    
                    return $subject;
                }
            }
        } catch (\Exception $e) {
            $this->logger->error('AI search plugin error', [
                'query' => $query,
                'error' => $e->getMessage()
            ]);
        }

        // Fallback to default Magento search
        return $proceed($query);
    }

    /**
     * Apply AI ranking to the collection
     *
     * @param Collection $collection
     * @param array $productIds
     * @return void
     */
    private function applyAIRanking(Collection $collection, array $productIds): void
    {
        // Create ORDER BY FIELD clause to maintain AI ranking order
        $orderExpression = 'FIELD(e.entity_id, ' . implode(',', $productIds) . ')';
        $collection->getSelect()->order(new \Zend_Db_Expr($orderExpression));
    }

    /**
     * Check if AI search is enabled
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