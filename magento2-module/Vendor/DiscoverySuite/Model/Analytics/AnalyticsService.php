<?php
/**
 * DiscoverySuite Analytics Service Implementation
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Model\Analytics;

use Vendor\DiscoverySuite\Api\AnalyticsInterface;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Magento\Framework\Exception\LocalizedException;
use Magento\Store\Model\StoreManagerInterface;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Framework\Session\SessionManagerInterface;
use Psr\Log\LoggerInterface;

class AnalyticsService implements AnalyticsInterface
{
    /**
     * @var HttpClient
     */
    private $httpClient;

    /**
     * @var StoreManagerInterface
     */
    private $storeManager;

    /**
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * @var SessionManagerInterface
     */
    private $sessionManager;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param HttpClient $httpClient
     * @param StoreManagerInterface $storeManager
     * @param CustomerSession $customerSession
     * @param SessionManagerInterface $sessionManager
     * @param LoggerInterface $logger
     */
    public function __construct(
        HttpClient $httpClient,
        StoreManagerInterface $storeManager,
        CustomerSession $customerSession,
        SessionManagerInterface $sessionManager,
        LoggerInterface $logger
    ) {
        $this->httpClient = $httpClient;
        $this->storeManager = $storeManager;
        $this->customerSession = $customerSession;
        $this->sessionManager = $sessionManager;
        $this->logger = $logger;
    }

    /**
     * @inheritDoc
     */
    public function trackEvent(
        string $eventType,
        array $eventData,
        ?int $customerId = null,
        ?string $sessionId = null,
        ?int $storeId = null
    ): bool {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();
            $customerId = $customerId ?: $this->customerSession->getCustomerId();
            $sessionId = $sessionId ?: $this->sessionManager->getSessionId();

            $trackingData = [
                'event_type' => $eventType,
                'event_data' => $eventData,
                'customer_id' => $customerId,
                'session_id' => $sessionId,
                'store_id' => $storeId,
                'timestamp' => date('Y-m-d H:i:s'),
                'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? '',
                'ip_address' => $this->getClientIp(),
                'referrer' => $_SERVER['HTTP_REFERER'] ?? ''
            ];

            $response = $this->httpClient->post('/events/track', $trackingData);

            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('Event tracking error', [
                'event_type' => $eventType,
                'customer_id' => $customerId,
                'error' => $e->getMessage()
            ]);

            return false;
        }
    }

    /**
     * @inheritDoc
     */
    public function trackPageView(
        string $pageType,
        string $pageUrl,
        array $pageData = [],
        ?int $customerId = null,
        ?string $sessionId = null,
        ?int $storeId = null
    ): bool {
        $eventData = array_merge($pageData, [
            'page_type' => $pageType,
            'page_url' => $pageUrl,
            'page_title' => $pageData['page_title'] ?? '',
            'load_time' => $pageData['load_time'] ?? null
        ]);

        return $this->trackEvent('page_view', $eventData, $customerId, $sessionId, $storeId);
    }

    /**
     * @inheritDoc
     */
    public function trackProductInteraction(
        int $productId,
        string $action,
        array $context = [],
        ?int $customerId = null,
        ?string $sessionId = null,
        ?int $storeId = null
    ): bool {
        $eventData = array_merge($context, [
            'product_id' => $productId,
            'action' => $action,
            'position' => $context['position'] ?? null,
            'list_name' => $context['list_name'] ?? null,
            'category_id' => $context['category_id'] ?? null
        ]);

        return $this->trackEvent('product_interaction', $eventData, $customerId, $sessionId, $storeId);
    }

    /**
     * @inheritDoc
     */
    public function trackConversion(
        array $orderData,
        ?int $customerId = null,
        ?string $sessionId = null,
        ?int $storeId = null
    ): bool {
        $eventData = [
            'order_id' => $orderData['order_id'] ?? null,
            'order_total' => $orderData['order_total'] ?? 0,
            'currency' => $orderData['currency'] ?? 'USD',
            'items' => $orderData['items'] ?? [],
            'payment_method' => $orderData['payment_method'] ?? null,
            'shipping_method' => $orderData['shipping_method'] ?? null
        ];

        return $this->trackEvent('conversion', $eventData, $customerId, $sessionId, $storeId);
    }

    /**
     * @inheritDoc
     */
    public function getDashboardData(
        string $period = 'week',
        ?int $storeId = null
    ): array {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $params = [
                'period' => $period,
                'store_id' => $storeId
            ];

            return $this->httpClient->get('/analytics/dashboard', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('Dashboard data error', [
                'period' => $period,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * @inheritDoc
     */
    public function getSearchAnalytics(
        string $period = 'week',
        ?int $storeId = null
    ): array {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $params = [
                'period' => $period,
                'store_id' => $storeId
            ];

            return $this->httpClient->get('/analytics/search', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('Search analytics error', [
                'period' => $period,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * @inheritDoc
     */
    public function getRecommendationAnalytics(
        string $period = 'week',
        ?int $storeId = null
    ): array {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $params = [
                'period' => $period,
                'store_id' => $storeId
            ];

            return $this->httpClient->get('/analytics/recommendations', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('Recommendation analytics error', [
                'period' => $period,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * @inheritDoc
     */
    public function getConversionAnalytics(
        string $period = 'week',
        ?int $storeId = null
    ): array {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $params = [
                'period' => $period,
                'store_id' => $storeId
            ];

            return $this->httpClient->get('/analytics/conversions', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('Conversion analytics error', [
                'period' => $period,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * @inheritDoc
     */
    public function getABTestResults(
        ?string $testId = null,
        ?int $storeId = null
    ): array {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $params = [
                'store_id' => $storeId
            ];

            if ($testId) {
                $params['test_id'] = $testId;
            }

            return $this->httpClient->get('/analytics/ab-tests', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('A/B test results error', [
                'test_id' => $testId,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * @inheritDoc
     */
    public function startABTest(
        string $testName,
        array $testConfig,
        ?int $storeId = null
    ): string {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $requestData = [
                'test_name' => $testName,
                'test_config' => $testConfig,
                'store_id' => $storeId
            ];

            $response = $this->httpClient->post('/analytics/ab-tests/start', $requestData);

            return $response['test_id'] ?? '';

        } catch (LocalizedException $e) {
            $this->logger->error('A/B test start error', [
                'test_name' => $testName,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return '';
        }
    }

    /**
     * @inheritDoc
     */
    public function stopABTest(string $testId): bool
    {
        try {
            $requestData = ['test_id' => $testId];

            $response = $this->httpClient->post('/analytics/ab-tests/stop', $requestData);

            return $response['success'] ?? false;

        } catch (LocalizedException $e) {
            $this->logger->error('A/B test stop error', [
                'test_id' => $testId,
                'error' => $e->getMessage()
            ]);

            return false;
        }
    }

    /**
     * @inheritDoc
     */
    public function getUserSegment(
        ?int $customerId = null,
        ?string $sessionId = null
    ): array {
        try {
            $customerId = $customerId ?: $this->customerSession->getCustomerId();
            $sessionId = $sessionId ?: $this->sessionManager->getSessionId();

            $params = [
                'customer_id' => $customerId,
                'session_id' => $sessionId
            ];

            return $this->httpClient->get('/analytics/user-segment', $params);

        } catch (LocalizedException $e) {
            $this->logger->error('User segment error', [
                'customer_id' => $customerId,
                'session_id' => $sessionId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * @inheritDoc
     */
    public function generateReport(
        string $reportType,
        array $reportParams = [],
        ?int $storeId = null
    ): array {
        try {
            $storeId = $storeId ?: $this->storeManager->getStore()->getId();

            $requestData = array_merge($reportParams, [
                'report_type' => $reportType,
                'store_id' => $storeId
            ]);

            return $this->httpClient->post('/analytics/reports/generate', $requestData);

        } catch (LocalizedException $e) {
            $this->logger->error('Report generation error', [
                'report_type' => $reportType,
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * Get client IP address
     *
     * @return string
     */
    private function getClientIp(): string
    {
        $ipKeys = ['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'HTTP_CLIENT_IP', 'REMOTE_ADDR'];
        
        foreach ($ipKeys as $key) {
            if (!empty($_SERVER[$key])) {
                $ip = $_SERVER[$key];
                // Handle comma-separated IPs (for forwarded headers)
                if (strpos($ip, ',') !== false) {
                    $ip = trim(explode(',', $ip)[0]);
                }
                return $ip;
            }
        }
        
        return '0.0.0.0';
    }
}