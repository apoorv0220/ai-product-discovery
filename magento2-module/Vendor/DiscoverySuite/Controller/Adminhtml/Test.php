<?php
/**
 * DiscoverySuite Admin Test Connection Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Controller\Adminhtml;

use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Magento\Backend\App\Action;
use Magento\Backend\App\Action\Context;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;

class Test extends Action
{
    /**
     * Authorization level
     */
    const ADMIN_RESOURCE = 'Vendor_DiscoverySuite::config';

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var HttpClient
     */
    private $httpClient;

    /**
     * @var JsonFactory
     */
    private $resultJsonFactory;

    /**
     * Constructor
     *
     * @param Context $context
     * @param Data $helper
     * @param HttpClient $httpClient
     * @param JsonFactory $resultJsonFactory
     */
    public function __construct(
        Context $context,
        Data $helper,
        HttpClient $httpClient,
        JsonFactory $resultJsonFactory
    ) {
        $this->helper = $helper;
        $this->httpClient = $httpClient;
        $this->resultJsonFactory = $resultJsonFactory;
        parent::__construct($context);
    }

    /**
     * Execute test connection
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->resultJsonFactory->create();

        try {
            $services = $this->testAllServices();
            $connected = 0;
            $total = count($services);

            foreach ($services as $service) {
                if ($service['connected']) {
                    $connected++;
                }
            }

            return $result->setData([
                'success' => true,
                'services' => $services,
                'connected' => $connected,
                'total' => $total,
                'message' => "Connected to {$connected} out of {$total} services"
            ]);

        } catch (\Exception $e) {
            return $result->setData([
                'success' => false,
                'message' => 'Test failed: ' . $e->getMessage()
            ]);
        }
    }

    /**
     * Test all AI services
     *
     * @return array
     */
    private function testAllServices(): array
    {
        $services = [
            '7001' => ['name' => 'Search Service', 'url' => $this->helper->getServiceUrl('search', '/health/')],
            '7002' => ['name' => 'Recommendation Service', 'url' => $this->helper->getServiceUrl('recommendation', '/health/')],
            '7003' => ['name' => 'Analytics Service', 'url' => $this->helper->getServiceUrl('analytics', '/health/')],
            '7004' => ['name' => 'Shopping Assistant', 'url' => $this->helper->getServiceUrl('shopping_assistant', '/health/')]
        ];

        $results = [];

        foreach ($services as $port => $service) {
            $startTime = microtime(true);
            
            try {
                // Create a specific HTTP client for this service
                $response = $this->makeHealthRequest($service['url']);
                $responseTime = round((microtime(true) - $startTime) * 1000);

                $results[$port] = [
                    'name' => $service['name'],
                    'connected' => isset($response['status']) && $response['status'] === 'healthy',
                    'response_time' => $responseTime,
                    'error' => null
                ];

            } catch (\Exception $e) {
                $responseTime = round((microtime(true) - $startTime) * 1000);
                $results[$port] = [
                    'name' => $service['name'],
                    'connected' => false,
                    'response_time' => $responseTime,
                    'error' => $e->getMessage()
                ];
            }
        }

        return $results;
    }

    /**
     * Make health check request
     *
     * @param string $url
     * @return array
     */
    private function makeHealthRequest(string $url): array
    {
        // Simple cURL request for health check
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
            'Accept: application/json'
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            throw new \Exception($error);
        }

        if ($httpCode !== 200) {
            throw new \Exception("HTTP {$httpCode}");
        }

        $data = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new \Exception('Invalid JSON response');
        }

        return $data;
    }
}