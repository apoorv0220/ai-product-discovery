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

use Magento\Framework\Api\Filter;
use Magento\Framework\Api\FilterBuilder;
use Magento\Framework\Api\Search\ReportingInterface;
use Magento\Framework\Api\Search\SearchCriteriaBuilder;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\View\Element\UiComponent\DataProvider\DataProvider;
use Vendor\DiscoverySuite\Api\AnalyticsInterface;

class AnalyticsDataProvider extends DataProvider
{
    /**
     * @var AnalyticsInterface
     */
    private $analyticsService;

    /**
     * @param string $name
     * @param string $primaryFieldName
     * @param string $requestFieldName
     * @param ReportingInterface $reporting
     * @param SearchCriteriaBuilder $searchCriteriaBuilder
     * @param RequestInterface $request
     * @param FilterBuilder $filterBuilder
     * @param AnalyticsInterface $analyticsService
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
    }

    /**
     * Get data
     *
     * @return array
     */
    public function getData(): array
    {
        try {
            // Get analytics data from service
            $analyticsData = $this->analyticsService->getDashboardData('week');
            
            // Transform data for UI component
            $items = [];
            if (isset($analyticsData['events']) && is_array($analyticsData['events'])) {
                foreach ($analyticsData['events'] as $event) {
                    $items[] = [
                        'id' => $event['id'] ?? '',
                        'event_type' => $event['event_type'] ?? '',
                        'user_id' => $event['user_id'] ?? '',
                        'session_id' => $event['session_id'] ?? '',
                        'store_id' => $event['store_id'] ?? '',
                        'page_url' => $event['page_url'] ?? '',
                        'device_type' => $event['device_type'] ?? '',
                        'created_at' => $event['created_at'] ?? ''
                    ];
                }
            }

            return [
                'totalRecords' => count($items),
                'items' => $items
            ];

        } catch (\Exception $e) {
            return [
                'totalRecords' => 0,
                'items' => []
            ];
        }
    }

    /**
     * Get meta data
     *
     * @return array
     */
    public function getMeta(): array
    {
        $meta = parent::getMeta();
        
        // Add custom meta data for analytics dashboard
        $meta['discovery_analytics_columns']['children']['summary'] = [
            'arguments' => [
                'data' => [
                    'config' => [
                        'componentType' => 'container',
                        'component' => 'Vendor_DiscoverySuite/js/dashboard/summary',
                        'displayArea' => 'dataGridFilters',
                        'dataScope' => '',
                        'label' => __('Analytics Summary'),
                        'provider' => $this->name,
                        'deps' => $this->name,
                        'imports' => [
                            'totalRecords' => '${ $.provider }:data.totalRecords'
                        ]
                    ]
                ]
            ]
        ];

        return $meta;
    }
}