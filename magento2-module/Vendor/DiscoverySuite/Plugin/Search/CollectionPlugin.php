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

use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\CatalogSearch\Model\ResourceModel\Fulltext\Collection;
use Magento\Framework\App\RequestInterface;
use Psr\Log\LoggerInterface;

class CollectionPlugin
{
    /**
     * @var SearchInterface
     */
    private $searchService;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var RequestInterface
     */
    private $request;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param SearchInterface $searchService
     * @param Data $helper
     * @param RequestInterface $request
     * @param LoggerInterface $logger
     */
    public function __construct(
        SearchInterface $searchService,
        Data $helper,
        RequestInterface $request,
        LoggerInterface $logger
    ) {
        $this->searchService = $searchService;
        $this->helper = $helper;
        $this->request = $request;
        $this->logger = $logger;
    }

    /**
     * Around method for load() to integrate AI search
     *
     * @param Collection $subject
     * @param callable $proceed
     * @param bool $printQuery
     * @param bool $logQuery
     * @return Collection
     */
    public function aroundLoad(Collection $subject, callable $proceed, $printQuery = false, $logQuery = false)
    {
        if (!$this->helper->isSearchEnabled()) {
            return $proceed($printQuery, $logQuery);
        }

        // Get search query from request
        $searchQuery = $this->request->getParam('q');
        
        if (!$searchQuery) {
            return $proceed($printQuery, $logQuery);
        }

        try {
            // Use AI search service for search results
            $aiSearchResults = $this->searchService->search(
                $searchQuery,
                (int) $subject->getPageSize(),
                (int) (($subject->getCurPage() - 1) * $subject->getPageSize()),
                $this->getFiltersFromRequest()
            );

            if (!empty($aiSearchResults['products'])) {
                // Extract product IDs from AI results
                $productIds = array_column($aiSearchResults['products'], 'id');
                
                // Apply AI search results to collection
                $subject->addFieldToFilter('entity_id', ['in' => $productIds]);
                
                // Preserve AI ordering
                if (count($productIds) > 1) {
                    $orderField = new \Zend_Db_Expr('FIELD(e.entity_id,' . implode(',', $productIds) . ')');
                    $subject->getSelect()->order($orderField);
                }

                $this->logger->info('AI search results applied', [
                    'query' => $searchQuery,
                    'ai_results_count' => count($productIds)
                ]);
            }

        } catch (\Exception $e) {
            $this->logger->error('AI search integration failed', [
                'query' => $searchQuery,
                'error' => $e->getMessage()
            ]);
            
            // Fall back to default Magento search
            return $proceed($printQuery, $logQuery);
        }

        return $proceed($printQuery, $logQuery);
    }

    /**
     * Get filters from current request
     *
     * @return array
     */
    private function getFiltersFromRequest(): array
    {
        $filters = [];
        
        // Price filter
        if ($priceFilter = $this->request->getParam('price')) {
            $priceRange = explode('-', $priceFilter);
            if (count($priceRange) === 2) {
                $filters['price'] = [
                    'min' => (float) $priceRange[0],
                    'max' => (float) $priceRange[1]
                ];
            }
        }

        // Category filter
        if ($categoryId = $this->request->getParam('cat')) {
            $filters['category_id'] = (int) $categoryId;
        }

        // Brand/manufacturer filter
        if ($brand = $this->request->getParam('brand')) {
            $filters['brand'] = $brand;
        }

        // Custom attribute filters
        foreach ($this->request->getParams() as $key => $value) {
            if (strpos($key, 'attr_') === 0) {
                $attributeCode = substr($key, 5);
                $filters['attributes'][$attributeCode] = $value;
            }
        }

        return $filters;
    }
}