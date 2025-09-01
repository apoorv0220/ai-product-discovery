<?php
/**
 * DiscoverySuite Search Autocomplete Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Controller\Search;

use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\App\Action\HttpGetActionInterface;
use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Psr\Log\LoggerInterface;

class Autocomplete implements HttpGetActionInterface, HttpPostActionInterface
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
     * @var JsonFactory
     */
    private $resultJsonFactory;

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
     * @param JsonFactory $resultJsonFactory
     * @param LoggerInterface $logger
     */
    public function __construct(
        SearchInterface $searchService,
        Data $helper,
        RequestInterface $request,
        JsonFactory $resultJsonFactory,
        LoggerInterface $logger
    ) {
        $this->searchService = $searchService;
        $this->helper = $helper;
        $this->request = $request;
        $this->resultJsonFactory = $resultJsonFactory;
        $this->logger = $logger;
    }

    /**
     * Execute autocomplete action
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->resultJsonFactory->create();

        if (!$this->helper->isAutocompleteEnabled()) {
            return $result->setData([
                'success' => false,
                'message' => 'Autocomplete is disabled',
                'suggestions' => []
            ]);
        }

        try {
            // Check if this is a product tracking request
            $action = $this->request->getParam('action');
            if ($action === 'track_product_view') {
                return $this->handleProductTracking($result);
            }

            $query = trim((string) $this->request->getParam('q', ''));
            $limit = (int) $this->request->getParam('limit', 10);

            if (strlen($query) < 2) {
                return $result->setData([
                    'success' => false,
                    'message' => 'Query too short',
                    'suggestions' => []
                ]);
            }

            // Get user ID and session ID for personalization
            $userId = $this->getUserId();
            $sessionId = $this->getSessionId();

            $autocompleteResponse = $this->searchService->autocomplete($query, $limit, $userId, $sessionId);
            
            // Process suggestions to ensure proper format
            $suggestions = [];
            if (isset($autocompleteResponse['suggestions']) && is_array($autocompleteResponse['suggestions'])) {
                $suggestions = $autocompleteResponse['suggestions'];
            } elseif (is_array($autocompleteResponse)) {
                $suggestions = $autocompleteResponse;
            }
            
            // Format suggestions to include required keys (title, image, price, url, category)
            $formattedSuggestions = [];
            $hasCorrections = false;
            $correctionMessage = '';
            
            foreach ($suggestions as $suggestion) {
                // Check for typo corrections
                if (isset($suggestion['is_corrected']) && $suggestion['is_corrected']) {
                    $hasCorrections = true;
                    if (isset($suggestion['corrected_from']) && isset($suggestion['corrected_to'])) {
                        $correctionMessage = sprintf(
                            'Showing results for "%s" (corrected from "%s")', 
                            $suggestion['corrected_to'], 
                            $suggestion['corrected_from']
                        );
                    }
                }
                
                $formattedSuggestions[] = [
                    'title' => $suggestion['suggestion'] ?? $suggestion['title'] ?? '',
                    'image' => $this->getFullImageUrl($suggestion['image'] ?? ''),
                    'price' => $this->formatPrice($suggestion['price'] ?? '$0.00'),
                    'url' => $this->getProductUrl($suggestion['url'] ?? '', (int)($suggestion['id'] ?? 0)),
                    'category' => $suggestion['category'] ?? 'General',
                    'type' => $suggestion['type'] ?? 'product',
                    'sku' => $suggestion['sku'] ?? '',
                    'id' => (int)($suggestion['id'] ?? 0),
                    'ai_enhanced' => true,
                    'is_corrected' => $suggestion['is_corrected'] ?? false,
                    'correction_confidence' => $suggestion['correction_confidence'] ?? 0
                ];
            }
            
            $responseData = [
                'success' => true,
                'query' => $query,
                'suggestions' => $formattedSuggestions
            ];
            
            // Add correction information if available
            if ($hasCorrections && $correctionMessage) {
                $responseData['correction_message'] = $correctionMessage;
                $responseData['has_corrections'] = true;
            }

            return $result->setData($responseData);

        } catch (\Exception $e) {
            $this->logger->error('Autocomplete request failed', [
                'query' => $this->request->getParam('q', ''),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'success' => false,
                'message' => 'Autocomplete request failed',
                'suggestions' => []
            ]);
        }
    }
    
    /**
     * Get full image URL
     *
     * @param string $imageUrl
     * @return string
     */
    private function getFullImageUrl(string $imageUrl): string
    {
        if (empty($imageUrl)) {
            return '';
        }
        
        // If it's already a full URL, return as is
        if (strpos($imageUrl, 'http') === 0) {
            return $imageUrl;
        }
        
        // If it's a relative URL, make it absolute
        $baseUrl = $this->request->getScheme() . '://' . $this->request->getHttpHost();
        return $baseUrl . '/' . ltrim($imageUrl, '/');
    }
    
    /**
     * Format price for display
     *
     * @param string $price
     * @return string
     */
    private function formatPrice(string $price): string
    {
        if (empty($price) || $price === '$0.00') {
            return 'Price on request';
        }
        
        // If it's already formatted, return as is
        if (strpos($price, '$') !== false || strpos($price, 'USD') !== false) {
            return $price;
        }
        
        // Try to format as currency
        if (is_numeric($price)) {
            return '$' . number_format((float)$price, 2);
        }
        
        return $price;
    }
    
    /**
     * Get product URL
     *
     * @param string $url
     * @param int $productId
     * @return string
     */
    private function getProductUrl(string $url, int $productId): string
    {
        if (!empty($url)) {
            // If it's already a full URL, return as is
            if (strpos($url, 'http') === 0) {
                return $url;
            }
            
            // If it's a relative URL, make it absolute
            $baseUrl = $this->request->getScheme() . '://' . $this->request->getHttpHost();
            return $baseUrl . '/' . ltrim($url, '/');
        }
        
        // Fallback: generate URL based on product ID
        if ($productId > 0) {
            $baseUrl = $this->request->getScheme() . '://' . $this->request->getHttpHost();
            return $baseUrl . '/product/view/id/' . $productId;
        }
        
        return '#';
    }

    /**
     * Get user ID for personalization
     *
     * @return string|null
     */
    private function getUserId(): ?string
    {
        // Try from request parameters first (for frontend JS)
        $userId = $this->request->getParam('user_id');
        if ($userId) {
            return (string) $userId;
        }
        
        // Try to get customer ID from session if available
        try {
            $objectManager = \Magento\Framework\App\ObjectManager::getInstance();
            $customerSession = $objectManager->get(\Magento\Customer\Model\Session::class);
            if ($customerSession && $customerSession->isLoggedIn()) {
                return (string) $customerSession->getCustomerId();
            }
        } catch (\Exception $e) {
            // Ignore session errors
        }
        
        return null;
    }

    /**
     * Get session ID for personalization
     *
     * @return string
     */
    private function getSessionId(): string
    {
        // Try from request parameters first (for frontend JS)
        $sessionId = $this->request->getParam('session_id');
        if ($sessionId) {
            return (string) $sessionId;
        }
        
        // Generate session ID based on PHP session or create new one
        try {
            if (session_status() === PHP_SESSION_ACTIVE) {
                return 'php_' . session_id();
            }
        } catch (\Exception $e) {
            // Ignore session errors
        }
        
        // Fallback: generate a basic session ID based on request info
        $userAgent = $this->request->getHeader('User-Agent') ?: 'unknown';
        $remoteAddr = $this->request->getClientIp() ?: '127.0.0.1';
        return 'sess_' . time() . '_' . substr(md5($userAgent . $remoteAddr), 0, 8);
    }

    /**
     * Handle product tracking requests
     *
     * @param ResultInterface $result
     * @return ResultInterface
     */
    private function handleProductTracking($result): ResultInterface
    {
        try {
            $trackingDataJson = $this->request->getParam('tracking_data');
            $trackingData = json_decode($trackingDataJson, true);
            
            if (!$trackingData || !isset($trackingData['product_id'])) {
                return $result->setData([
                    'success' => false,
                    'message' => 'Invalid tracking data'
                ]);
            }

            // Make API call to backend tracking service
            $apiData = [
                'session_id' => $trackingData['session_id'] ?? $this->getSessionId(),
                'product_id' => (string) $trackingData['product_id'],
                'product_name' => $trackingData['product_name'] ?? '',
                'product_sku' => $trackingData['product_sku'] ?? '',
                'categories' => $trackingData['categories'] ?? [],
                'came_from_search' => (bool) ($trackingData['came_from_search'] ?? false),
                'search_query' => $trackingData['search_query'] ?? ''
            ];

            // Use cURL to call backend API
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, 'http://localhost:7001/api/v1/tracking/product-view');
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($apiData));
            curl_setopt($ch, CURLOPT_HTTPHEADER, [
                'Content-Type: application/json',
                'Accept: application/json'
            ]);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 3);
            
            $response = curl_exec($ch);
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            
            if ($httpCode === 200 && $response) {
                $responseData = json_decode($response, true);
                if ($responseData && isset($responseData['success']) && $responseData['success']) {
                    return $result->setData([
                        'success' => true,
                        'message' => 'Product view tracked successfully'
                    ]);
                }
            }
            
            // Return success even if backend fails (graceful degradation)
            return $result->setData([
                'success' => true,
                'message' => 'Product view tracked (offline mode)'
            ]);

        } catch (\Exception $e) {
            // Log error but return success for graceful degradation
            $this->logger->warning('Product tracking error: ' . $e->getMessage());
            
            return $result->setData([
                'success' => true,
                'message' => 'Product view tracked (fallback mode)'
            ]);
        }
    }
}