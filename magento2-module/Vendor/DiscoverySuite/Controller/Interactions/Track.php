<?php
/**
 * Interaction Tracking Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Controller\Interactions;

use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Exception\LocalizedException;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Psr\Log\LoggerInterface;

class Track implements HttpPostActionInterface
{
    /**
     * @var JsonFactory
     */
    private $jsonFactory;

    /**
     * @var RequestInterface
     */
    private $request;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var HttpClient
     */
    private $httpClient;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param JsonFactory $jsonFactory
     * @param RequestInterface $request
     * @param Data $helper
     * @param HttpClient $httpClient
     * @param LoggerInterface $logger
     */
    public function __construct(
        JsonFactory $jsonFactory,
        RequestInterface $request,
        Data $helper,
        HttpClient $httpClient,
        LoggerInterface $logger
    ) {
        $this->jsonFactory = $jsonFactory;
        $this->request = $request;
        $this->helper = $helper;
        $this->httpClient = $httpClient;
        $this->logger = $logger;
    }

    /**
     * Track user interaction
     *
     * @return \Magento\Framework\Controller\Result\Json
     */
    public function execute()
    {
        $result = $this->jsonFactory->create();
        
        try {
            if (!$this->helper->isEnabled()) {
                throw new LocalizedException(__('DiscoverySuite is not enabled'));
            }

            $postData = $this->request->getPostValue();
            
            if (empty($postData)) {
                // Try to get JSON data from request body
                $content = $this->request->getContent();
                $postData = json_decode($content, true);
            }

            if (empty($postData)) {
                throw new LocalizedException(__('No tracking data provided'));
            }

            $interactionType = $postData['interaction_type'] ?? 'unknown';
            
            // Forward to backend API
            $endpoint = $this->helper->getServiceUrl('search', '/api/v1/interactions/');
            
            switch ($interactionType) {
                case 'product_view':
                    $response = $this->trackProductView($endpoint, $postData);
                    break;
                    
                case 'search_query':
                    $response = $this->trackSearchQuery($endpoint, $postData);
                    break;
                    
                case 'page_view':
                    $response = $this->trackPageView($endpoint, $postData);
                    break;
                    
                default:
                    throw new LocalizedException(__('Invalid interaction type: %1', $interactionType));
            }

            $this->logger->info('Interaction tracked successfully', [
                'type' => $interactionType,
                'data' => $postData
            ]);

            return $result->setData([
                'success' => true,
                'message' => 'Interaction tracked successfully',
                'data' => $response
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Failed to track interaction: ' . $e->getMessage(), [
                'exception' => $e,
                'post_data' => $postData ?? []
            ]);

            return $result->setData([
                'success' => false,
                'message' => $e->getMessage()
            ])->setHttpResponseCode(500);
        }
    }

    /**
     * Track product view
     *
     * @param string $endpoint
     * @param array $data
     * @return array
     */
    private function trackProductView(string $endpoint, array $data): array
    {
        $trackingData = [
            'user_id' => $data['user_id'] ?? 'anonymous',
            'product_id' => $data['product_id'] ?? '',
            'product_name' => $data['product_name'] ?? '',
            'categories' => $data['categories'] ?? [],
            'session_id' => $data['session_id'] ?? ''
        ];

        $response = $this->httpClient->post($endpoint . 'product-view', $trackingData);
        
        return $response ?? [];
    }

    /**
     * Track search query
     *
     * @param string $endpoint
     * @param array $data
     * @return array
     */
    private function trackSearchQuery(string $endpoint, array $data): array
    {
        $trackingData = [
            'user_id' => $data['user_id'] ?? 'anonymous',
            'query' => $data['query'] ?? '',
            'results' => $data['results'] ?? [],
            'session_id' => $data['session_id'] ?? ''
        ];

        $response = $this->httpClient->post($endpoint . 'search-query', $trackingData);
        
        return $response ?? [];
    }

    /**
     * Track page view
     *
     * @param string $endpoint
     * @param string $data
     * @return array
     */
    private function trackPageView(string $endpoint, array $data): array
    {
        $trackingData = [
            'user_id' => $data['user_id'] ?? 'anonymous',
            'page_url' => $data['page_url'] ?? '',
            'page_title' => $data['page_title'] ?? '',
            'session_id' => $data['session_id'] ?? '',
            'timestamp' => $data['timestamp'] ?? ''
        ];

        $response = $this->httpClient->post($endpoint . 'page-view', $trackingData);
        
        return $response ?? [];
    }
}
