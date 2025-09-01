<?php
/**
 * Product View Tracking Controller
 * Handles product page view tracking for personalized search
 */

namespace Vendor\DiscoverySuite\Controller\Tracking;

use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\Action\Action;
use Magento\Framework\App\Action\Context;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Psr\Log\LoggerInterface;
use Vendor\DiscoverySuite\Helper\Data as DiscoveryHelper;

class ProductView extends Action implements HttpPostActionInterface
{
    /**
     * @var JsonFactory
     */
    private $jsonFactory;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @var DiscoveryHelper
     */
    private $helper;

    /**
     * @var \Magento\Framework\HTTP\Client\Curl
     */
    private $curl;

    /**
     * Constructor
     *
     * @param Context $context
     * @param JsonFactory $jsonFactory
     * @param LoggerInterface $logger
     * @param DiscoveryHelper $helper
     * @param \Magento\Framework\HTTP\Client\Curl $curl
     */
    public function __construct(
        Context $context,
        JsonFactory $jsonFactory,
        LoggerInterface $logger,
        DiscoveryHelper $helper,
        \Magento\Framework\HTTP\Client\Curl $curl
    ) {
        parent::__construct($context);
        $this->jsonFactory = $jsonFactory;
        $this->logger = $logger;
        $this->helper = $helper;
        $this->curl = $curl;
    }

    /**
     * Execute product view tracking
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->jsonFactory->create();

        try {
            // Get tracking data from request
            $request = $this->getRequest();
            $productId = $request->getParam('product_id');
            $productName = $request->getParam('product_name', '');
            $sessionId = $request->getParam('session_id', '');

            if (!$productId) {
                return $result->setData([
                    'success' => false,
                    'message' => 'Product ID is required'
                ]);
            }

            // Generate session ID if not provided
            if (!$sessionId) {
                $sessionId = 'sess_' . time() . '_' . uniqid();
            }

            // Prepare tracking data for backend API
            $trackingData = [
                'session_id' => $sessionId,
                'product_id' => (string) $productId,
                'product_name' => $productName,
                'came_from_search' => (bool) $request->getParam('came_from_search', false),
                'search_query' => $request->getParam('search_query', '')
            ];

            // Send to backend tracking API
            $backendUrl = 'http://localhost:7001/api/v1/tracking/product-view';
            
            $this->curl->setHeaders([
                'Content-Type: application/json',
                'Accept: application/json'
            ]);
            
            $this->curl->post($backendUrl, json_encode($trackingData));
            
            $response = $this->curl->getBody();
            $httpStatus = $this->curl->getStatus();
            
            if ($httpStatus === 200) {
                $responseData = json_decode($response, true);
                if ($responseData && isset($responseData['success']) && $responseData['success']) {
                    $this->logger->info('Product view tracked successfully', [
                        'product_id' => $productId,
                        'session_id' => $sessionId
                    ]);
                    
                    return $result->setData([
                        'success' => true,
                        'message' => 'Product view tracked successfully'
                    ]);
                }
            }
            
            // If we get here, something went wrong
            $this->logger->warning('Product view tracking failed', [
                'product_id' => $productId,
                'session_id' => $sessionId,
                'http_status' => $httpStatus,
                'response' => $response
            ]);
            
            return $result->setData([
                'success' => false,
                'message' => 'Failed to track product view'
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Product view tracking exception', [
                'message' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return $result->setData([
                'success' => false,
                'message' => 'An error occurred while tracking product view'
            ]);
        }
    }
}