<?php
/**
 * DiscoverySuite Test Connection Console Command
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Console\Command;

use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Helper\Table;
use Magento\Framework\App\State;
use Magento\Framework\App\Area;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;

class TestConnection extends Command
{
    /**
     * @var State
     */
    private $appState;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var HttpClient
     */
    private $httpClient;

    /**
     * Constructor
     *
     * @param State $appState
     * @param Data $helper
     * @param HttpClient $httpClient
     * @param string|null $name
     */
    public function __construct(
        State $appState,
        Data $helper,
        HttpClient $httpClient,
        string $name = null
    ) {
        $this->appState = $appState;
        $this->helper = $helper;
        $this->httpClient = $httpClient;
        parent::__construct($name);
    }

    /**
     * Configure command
     */
    protected function configure()
    {
        $this->setName('discovery:test:connection')
            ->setDescription('Test connection to all AI Discovery Suite services');
    }

    /**
     * Execute command
     *
     * @param InputInterface $input
     * @param OutputInterface $output
     * @return int
     */
    protected function execute(InputInterface $input, OutputInterface $output)
    {
        try {
            $this->appState->setAreaCode(Area::AREA_ADMINHTML);

            $output->writeln('<info>Testing AI Discovery Suite connections...</info>');
            $output->writeln('');

            if (!$this->helper->isEnabled()) {
                $output->writeln('<error>Discovery Suite is not enabled. Please enable it in configuration.</error>');
                return Command::FAILURE;
            }

            // Test all services
            $services = $this->getServicesToTest();
            $results = [];
            $allPassed = true;

            foreach ($services as $serviceName => $config) {
                $output->writeln("<info>Testing {$serviceName}...</info>");
                $result = $this->testService($config);
                $results[] = [
                    'Service' => $serviceName,
                    'URL' => $config['url'],
                    'Status' => $result['status'] ? '<info>✓ Connected</info>' : '<error>✗ Failed</error>',
                    'Response Time' => $result['response_time'] . 'ms',
                    'Message' => $result['message']
                ];
                
                if (!$result['status']) {
                    $allPassed = false;
                }
            }

            // Display results table
            $output->writeln('');
            $output->writeln('<info>Connection Test Results:</info>');
            $table = new Table($output);
            $table->setHeaders(['Service', 'URL', 'Status', 'Response Time', 'Message']);
            $table->setRows($results);
            $table->render();

            if ($allPassed) {
                $output->writeln('');
                $output->writeln('<info>All services are connected successfully!</info>');
                return Command::SUCCESS;
            } else {
                $output->writeln('');
                $output->writeln('<error>Some services failed to connect. Please check your configuration.</error>');
                return Command::FAILURE;
            }

        } catch (\Exception $e) {
            $output->writeln('<error>Error during connection test: ' . $e->getMessage() . '</error>');
            return Command::FAILURE;
        }
    }

    /**
     * Get services to test
     *
     * @return array
     */
    private function getServicesToTest(): array
    {
        $baseUrl = $this->helper->getApiBaseUrl();
        
        return [
            'Search Service' => [
                'url' => $baseUrl . ':' . $this->helper->getSearchServicePort() . '/health/',
                'endpoint' => '/health/'
            ],
            'Recommendation Service' => [
                'url' => $baseUrl . ':' . $this->helper->getRecommendationServicePort() . '/health/',
                'endpoint' => '/health/'
            ],
            'Analytics Service' => [
                'url' => $baseUrl . ':' . $this->helper->getAnalyticsServicePort() . '/health/',
                'endpoint' => '/health/'
            ],
            'Shopping Assistant' => [
                'url' => $baseUrl . ':' . $this->helper->getShoppingAssistantPort() . '/health/',
                'endpoint' => '/health/'
            ]
        ];
    }

    /**
     * Test individual service
     *
     * @param array $config
     * @return array
     */
    private function testService(array $config): array
    {
        // Use the new testConnectionToUrl method that handles mixed HTTP/HTTPS properly
        return $this->httpClient->testConnectionToUrl($config['url']);
    }
}