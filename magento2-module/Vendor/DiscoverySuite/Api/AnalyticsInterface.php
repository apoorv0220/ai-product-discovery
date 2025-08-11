<?php
/**
 * DiscoverySuite Analytics Interface
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Api;

interface AnalyticsInterface
{
    /**
     * Track event
     *
     * @param string $eventType
     * @param array $eventData
     * @param string|null $userId
     * @return bool
     */
    public function trackEvent(string $eventType, array $eventData, ?string $userId = null): bool;

    /**
     * Get analytics dashboard data
     *
     * @param string $dateFrom
     * @param string $dateTo
     * @param array $filters
     * @return array
     */
    public function getDashboardData(string $dateFrom, string $dateTo, array $filters = []): array;

    /**
     * Get performance reports
     *
     * @param string $reportType
     * @param array $parameters
     * @return array
     */
    public function getReport(string $reportType, array $parameters = []): array;
}