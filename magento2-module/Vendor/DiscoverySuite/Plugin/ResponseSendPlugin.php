<?php
namespace Vendor\DiscoverySuite\Plugin;

use Exception;
use Magento\Framework\App\Response\Http;
use Vendor\DiscoverySuite\Model\BulkDataCollector;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Psr\Log\LoggerInterface;

class ResponseSendPlugin
{
    /**
     * @var BulkDataCollector
     */
    private $collector;

    /**
     * @var HttpClient
     */
    private $httpClient;

    /**
     * @var LoggerInterface
     */
    private $logger;

    public function __construct(
        BulkDataCollector $collector,
        HttpClient $httpClient,
        LoggerInterface $logger
    ) {
        $this->collector  = $collector;
        $this->httpClient = $httpClient;
        $this->logger     = $logger;
    }

    public function afterSendResponse(
        Http $subject,
        $result
    ) {
        if ($this->collector->isEmpty()) {
            return $result;
        }

        $payload = $this->collector->getPayload();

        try {
            // Debug payload
            $this->logger->debug('DiscoverySuite bulk payload', [
                'payload' => $payload
            ]);

            $response = $this->httpClient->post(
                '/api/v1/tracking/bulk-ingest',
                $payload
            );

            // Log API response
            $this->logger->info('DiscoverySuite bulk ingest response', [
                'response' => $response
            ]);

        } catch (Exception $e) {
            $this->logger->error('DiscoverySuite bulk ingest failed', [
                'error'   => $e->getMessage(),
                'trace'   => $e->getTraceAsString()
            ]);
        }

        return $result;
    }
}
