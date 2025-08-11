<?php
/**
 * DiscoverySuite HTTP Client for API Communication
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Model\Api;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\GuzzleException;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Framework\Exception\LocalizedException;
use Magento\Store\Model\ScopeInterface;
use Psr\Log\LoggerInterface;

class HttpClient
{
    /**
     * @var Client
     */
    private $httpClient;

    /**
     * @var ScopeConfigInterface
     */
    private $scopeConfig;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @var string
     */
    private $baseUri;

    /**
     * @var string
     */
    private $defaultPort;

    /**
     * Configuration paths
     */
    const XML_PATH_ENABLED = 'discovery_suite/general/enabled';
    const XML_PATH_API_BASE_URL = 'discovery_suite/general/api_base_url';
    const XML_PATH_API_KEY = 'discovery_suite/general/api_key';
    const XML_PATH_TIMEOUT = 'discovery_suite/general/timeout';
    const XML_PATH_DEBUG_MODE = 'discovery_suite/general/debug_mode';

    /**
     * @param ScopeConfigInterface $scopeConfig
     * @param LoggerInterface $logger
     * @param string $baseUri
     * @param string $defaultPort
     */
    public function __construct(
        ScopeConfigInterface $scopeConfig,
        LoggerInterface $logger,
        string $baseUri = '',
        string $defaultPort = '7099'
    ) {
        $this->scopeConfig = $scopeConfig;
        $this->logger = $logger;
        $this->baseUri = $baseUri;
        $this->defaultPort = $defaultPort;
        $this->initializeHttpClient();
    }

    /**
     * Initialize HTTP client with configuration
     */
    private function initializeHttpClient(): void
    {
        $baseUrl = $this->getBaseUrl();
        $timeout = (int) $this->scopeConfig->getValue(
            self::XML_PATH_TIMEOUT,
            ScopeInterface::SCOPE_STORE
        ) ?: 30;

        $this->httpClient = new Client([
            'base_uri' => $baseUrl,
            'timeout' => $timeout,
            'verify' => false, // For development - should be true in production
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
                'User-Agent' => 'Magento2-DiscoverySuite/1.0'
            ]
        ]);
    }

    /**
     * Get base URL for API service
     *
     * @return string
     */
    private function getBaseUrl(): string
    {
        $baseUrl = $this->scopeConfig->getValue(
            self::XML_PATH_API_BASE_URL,
            ScopeInterface::SCOPE_STORE
        );

        if (!$baseUrl) {
            $baseUrl = 'http://localhost';
        }

        // Add service-specific port
        $baseUrl = rtrim($baseUrl, '/') . ':' . $this->defaultPort;

        return $baseUrl;
    }

    /**
     * Get API key from configuration
     *
     * @return string|null
     */
    private function getApiKey(): ?string
    {
        return $this->scopeConfig->getValue(
            self::XML_PATH_API_KEY,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if module is enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return (bool) $this->scopeConfig->getValue(
            self::XML_PATH_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if debug mode is enabled
     *
     * @return bool
     */
    private function isDebugMode(): bool
    {
        return (bool) $this->scopeConfig->getValue(
            self::XML_PATH_DEBUG_MODE,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Make GET request
     *
     * @param string $endpoint
     * @param array $params
     * @return array
     * @throws LocalizedException
     */
    public function get(string $endpoint, array $params = []): array
    {
        return $this->makeRequest('GET', $endpoint, ['query' => $params]);
    }

    /**
     * Make POST request
     *
     * @param string $endpoint
     * @param array $data
     * @return array
     * @throws LocalizedException
     */
    public function post(string $endpoint, array $data = []): array
    {
        return $this->makeRequest('POST', $endpoint, ['json' => $data]);
    }

    /**
     * Make PUT request
     *
     * @param string $endpoint
     * @param array $data
     * @return array
     * @throws LocalizedException
     */
    public function put(string $endpoint, array $data = []): array
    {
        return $this->makeRequest('PUT', $endpoint, ['json' => $data]);
    }

    /**
     * Make DELETE request
     *
     * @param string $endpoint
     * @param array $params
     * @return array
     * @throws LocalizedException
     */
    public function delete(string $endpoint, array $params = []): array
    {
        return $this->makeRequest('DELETE', $endpoint, ['query' => $params]);
    }

    /**
     * Make HTTP request
     *
     * @param string $method
     * @param string $endpoint
     * @param array $options
     * @return array
     * @throws LocalizedException
     */
    private function makeRequest(string $method, string $endpoint, array $options = []): array
    {
        if (!$this->isEnabled()) {
            throw new LocalizedException(__('DiscoverySuite module is disabled'));
        }

        try {
            // Add API key to headers if available
            $apiKey = $this->getApiKey();
            if ($apiKey) {
                $options['headers']['Authorization'] = 'Bearer ' . $apiKey;
            }

            if ($this->isDebugMode()) {
                $this->logger->debug('DiscoverySuite API Request', [
                    'method' => $method,
                    'endpoint' => $endpoint,
                    'options' => $options
                ]);
            }

            $response = $this->httpClient->request($method, $endpoint, $options);
            $body = $response->getBody()->getContents();
            $data = json_decode($body, true);

            if ($this->isDebugMode()) {
                $this->logger->debug('DiscoverySuite API Response', [
                    'status' => $response->getStatusCode(),
                    'data' => $data
                ]);
            }

            if (json_last_error() !== JSON_ERROR_NONE) {
                throw new LocalizedException(__('Invalid JSON response from API'));
            }

            return $data ?: [];

        } catch (GuzzleException $e) {
            $this->logger->error('DiscoverySuite API Error', [
                'method' => $method,
                'endpoint' => $endpoint,
                'error' => $e->getMessage()
            ]);

            throw new LocalizedException(
                __('API request failed: %1', $e->getMessage())
            );
        }
    }

    /**
     * Test API connection
     *
     * @return bool
     */
    public function testConnection(): bool
    {
        try {
            $this->get('/health');
            return true;
        } catch (LocalizedException $e) {
            $this->logger->warning('DiscoverySuite API connection test failed', [
                'error' => $e->getMessage()
            ]);
            return false;
        }
    }

    /**
     * Get service health status
     *
     * @return array
     */
    public function getHealthStatus(): array
    {
        try {
            return $this->get('/health');
        } catch (LocalizedException $e) {
            return [
                'status' => 'error',
                'message' => $e->getMessage()
            ];
        }
    }
}