<?php
/**
 * DiscoverySuite Analytics API Interface
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Api;

interface AnalyticsInterface
{
    /**
     * Track a custom event
     *
     * @param string $eventType Event type
     * @param array $eventData Event data
     * @param int|null $customerId Customer ID
     * @param string|null $sessionId Session ID
     * @param int|null $storeId Store ID
     * @return bool Success status
     */
    public function trackEvent(
        string $eventType,
        array $eventData,
        ?int $customerId = null,
        ?string $sessionId = null,
        ?int $storeId = null
    ): bool;

    /**
     * Track page view
     *
     * @param string $pageType Page type
     * @param string $pageUrl Page URL
     * @param array $pageData Additional page data
     * @param int|null $customerId Customer ID
     * @param string|null $sessionId Session ID
     * @param int|null $storeId Store ID
     * @return bool Success status
     */
    public function trackPageView(
        string $pageType,
        string $pageUrl,
        array $pageData = [],
        ?int $customerId = null,
        ?string $sessionId = null,
        ?int $storeId = null
    ): bool;

    /**
     * Track product interaction
     *
     * @param int $productId Product ID
     * @param string $action Action type (view, click, add_to_cart, purchase, etc.)
     * @param array $context Context data
     * @param int|null $customerId Customer ID
     * @param string|null $sessionId Session ID
     * @param int|null $storeId Store ID
     * @return bool Success status
     */
    public function trackProductInteraction(
        int $productId,
        string $action,
        array $context = [],
        ?int $customerId = null,
        ?string $sessionId = null,
        ?int $storeId = null
    ): bool;

    /**
     * Track conversion event
     *
     * @param array $orderData Order data
     * @param int|null $customerId Customer ID
     * @param string|null $sessionId Session ID
     * @param int|null $storeId Store ID
     * @return bool Success status
     */
    public function trackConversion(
        array $orderData,
        ?int $customerId = null,
        ?string $sessionId = null,
        ?int $storeId = null
    ): bool;

    /**
     * Get dashboard analytics data
     *
     * @param string $period Time period (day, week, month, year)
     * @param int|null $storeId Store ID
     * @return array Dashboard data
     */
    public function getDashboardData(
        string $period = 'week',
        ?int $storeId = null
    ): array;

    /**
     * Get search analytics
     *
     * @param string $period Time period
     * @param int|null $storeId Store ID
     * @return array Search analytics data
     */
    public function getSearchAnalytics(
        string $period = 'week',
        ?int $storeId = null
    ): array;

    /**
     * Get recommendation analytics
     *
     * @param string $period Time period
     * @param int|null $storeId Store ID
     * @return array Recommendation analytics data
     */
    public function getRecommendationAnalytics(
        string $period = 'week',
        ?int $storeId = null
    ): array;

    /**
     * Get conversion analytics
     *
     * @param string $period Time period
     * @param int|null $storeId Store ID
     * @return array Conversion analytics data
     */
    public function getConversionAnalytics(
        string $period = 'week',
        ?int $storeId = null
    ): array;

    /**
     * Get A/B test results
     *
     * @param string|null $testId Test ID (null for all active tests)
     * @param int|null $storeId Store ID
     * @return array A/B test results
     */
    public function getABTestResults(
        ?string $testId = null,
        ?int $storeId = null
    ): array;

    /**
     * Start A/B test
     *
     * @param string $testName Test name
     * @param array $testConfig Test configuration
     * @param int|null $storeId Store ID
     * @return string Test ID
     */
    public function startABTest(
        string $testName,
        array $testConfig,
        ?int $storeId = null
    ): string;

    /**
     * Stop A/B test
     *
     * @param string $testId Test ID
     * @return bool Success status
     */
    public function stopABTest(string $testId): bool;

    /**
     * Get user segment
     *
     * @param int|null $customerId Customer ID
     * @param string|null $sessionId Session ID
     * @return array User segment data
     */
    public function getUserSegment(
        ?int $customerId = null,
        ?string $sessionId = null
    ): array;

    /**
     * Generate custom report
     *
     * @param string $reportType Report type
     * @param array $reportParams Report parameters
     * @param int|null $storeId Store ID
     * @return array Report data
     */
    public function generateReport(
        string $reportType,
        array $reportParams = [],
        ?int $storeId = null
    ): array;
}