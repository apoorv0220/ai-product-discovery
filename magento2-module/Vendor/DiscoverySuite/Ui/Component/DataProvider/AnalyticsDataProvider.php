<?php
/**
 * DiscoverySuite Analytics Data Provider
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Ui\Component\DataProvider;

use Vendor\DiscoverySuite\Api\AnalyticsInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\Api\Search\ReportingInterface;
use Magento\Framework\Api\Search\SearchCriteriaBuilder;
use Magento\Framework\Api\FilterBuilder;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\View\Element\UiComponent\DataProvider\DataProvider;

class AnalyticsDataProvider extends DataProvider
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
     * Constructor
     *
     * @param string $name
     * @param string $primaryFieldName
     * @param string $requestFieldName
     * @param ReportingInterface $reporting
     * @param SearchCriteriaBuilder $searchCriteriaBuilder
     * @param RequestInterface $request
     * @param FilterBuilder $filterBuilder
     * @param AnalyticsInterface $analyticsService
     * @param Data $helper
     * @param array $meta
     * @param array $data
     */
    public function __construct(
        $name,
        $primaryFieldName,
        $requestFieldName,
        ReportingInterface $reporting,
        SearchCriteriaBuilder $searchCriteriaBuilder,
        RequestInterface $request,
        FilterBuilder $filterBuilder,
        AnalyticsInterface $analyticsService,
        Data $helper,
        array $meta = [],
        array $data = []
    ) {
        parent::__construct(
            $name,
            $primaryFieldName,
            $requestFieldName,
            $reporting,
            $searchCriteriaBuilder,
            $request,
            $filterBuilder,
            $meta,
            $data
        );
        $this->analyticsService = $analyticsService;
        $this->helper = $helper;
    }

    /**
     * Get data
     *
     * @return array
     */
    public function getData()
    {
        if (!$this->helper->isAnalyticsEnabled()) {
            return [
                'totalRecords' => 0,
                'items' => []
            ];
        }

        try {
            // Get date range from request
            $dateFrom = $this->request->getParam('date_from', date('Y-m-d', strtotime('-30 days')));
            $dateTo = $this->request->getParam('date_to', date('Y-m-d'));
            
            // Get filters
            $filters = $this->getFilters();

            // Get dashboard data from analytics service
            $analyticsData = $this->analyticsService->getDashboardData($dateFrom, $dateTo, $filters);

            return $this->formatDataForGrid($analyticsData);

        } catch (\Exception $e) {
            return [
                'totalRecords' => 0,
                'items' => [],
                'errorMessage' => $e->getMessage()
            ];
        }
    }

    /**
     * Get filters from request
     *
     * @return array
     */
    private function getFilters(): array
    {
        $filters = [];

        if ($storeId = $this->request->getParam('store_id')) {
            $filters['store_id'] = $storeId;
        }

        if ($eventType = $this->request->getParam('event_type')) {
            $filters['event_type'] = $eventType;
        }

        return $filters;
    }

    /**
     * Format analytics data for grid display
     *
     * @param array $analyticsData
     * @return array
     */
    private function formatDataForGrid(array $analyticsData): array
    {
        $items = [];

        if (isset($analyticsData['events'])) {
            foreach ($analyticsData['events'] as $index => $event) {
                $items[] = [
                    'id' => $index + 1,
                    'event_type' => $event['event_type'] ?? '',
                    'count' => $event['count'] ?? 0,
                    'conversion_rate' => isset($event['conversion_rate']) ? 
                        number_format($event['conversion_rate'] * 100, 2) . '%' : 'N/A',
                    'revenue' => isset($event['revenue']) ? 
                        '$' . number_format($event['revenue'], 2) : 'N/A',
                    'date' => $event['date'] ?? date('Y-m-d')
                ];
            }
        }

        return [
            'totalRecords' => count($items),
            'items' => $items
        ];
    }
}