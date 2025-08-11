<?php
/**
 * DiscoverySuite Sync Catalog Console Command
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
use Symfony\Component\Console\Input\InputOption;
use Magento\Framework\App\State;
use Magento\Framework\App\Area;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;

class SyncCatalog extends Command
{
    const BATCH_SIZE = 'batch-size';
    const STORE_ID = 'store-id';

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
        $this->setName('discovery:sync:catalog')
            ->setDescription('Sync product catalog with AI Discovery Suite')
            ->addOption(
                self::BATCH_SIZE,
                'b',
                InputOption::VALUE_OPTIONAL,
                'Batch size for syncing products',
                100
            )
            ->addOption(
                self::STORE_ID,
                's',
                InputOption::VALUE_OPTIONAL,
                'Store ID to sync',
                1
            );
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
            
            $batchSize = (int)$input->getOption(self::BATCH_SIZE);
            $storeId = (int)$input->getOption(self::STORE_ID);

            $output->writeln('<info>Starting catalog sync...</info>');
            $output->writeln("Batch size: {$batchSize}");
            $output->writeln("Store ID: {$storeId}");

            if (!$this->helper->isEnabled()) {
                $output->writeln('<error>Discovery Suite is not enabled. Please enable it in configuration.</error>');
                return Command::FAILURE;
            }

            // Test API connection first
            $output->writeln('<info>Testing API connection...</info>');
            $isConnected = $this->testApiConnection($output);
            
            if (!$isConnected) {
                $output->writeln('<error>API connection failed. Please check your configuration.</error>');
                return Command::FAILURE;
            }

            $output->writeln('<info>API connection successful!</info>');

            // Sync products in batches
            $totalSynced = $this->syncProducts($batchSize, $storeId, $output);

            $output->writeln("<info>Catalog sync completed successfully! Synced {$totalSynced} products.</info>");
            return Command::SUCCESS;

        } catch (\Exception $e) {
            $output->writeln('<error>Error during catalog sync: ' . $e->getMessage() . '</error>');
            return Command::FAILURE;
        }
    }

    /**
     * Test API connection
     *
     * @param OutputInterface $output
     * @return bool
     */
    private function testApiConnection(OutputInterface $output): bool
    {
        try {
            $searchEndpoint = $this->helper->getApiBaseUrl() . ':' . $this->helper->getSearchServicePort() . '/health/';
            $response = $this->httpClient->get($searchEndpoint);
            
            if (!empty($response['status']) && $response['status'] === 'healthy') {
                return true;
            }
            
            return false;
        } catch (\Exception $e) {
            $output->writeln('<comment>API connection test failed: ' . $e->getMessage() . '</comment>');
            return false;
        }
    }

    /**
     * Sync products to discovery service
     *
     * @param int $batchSize
     * @param int $storeId
     * @param OutputInterface $output
     * @return int
     */
    private function syncProducts(int $batchSize, int $storeId, OutputInterface $output): int
    {
        $totalSynced = 0;
        
        // This is a placeholder - in a real implementation, you would:
        // 1. Load products from Magento catalog
        // 2. Format them for the API
        // 3. Send them to the search service indexing endpoint
        // 4. Handle any errors and retry logic
        
        $output->writeln('<comment>Product sync functionality to be implemented based on your catalog structure.</comment>');
        $output->writeln('<comment>This command will sync products to: ' . $this->helper->getApiBaseUrl() . ':' . $this->helper->getSearchServicePort() . '/api/v1/index/</comment>');
        
        return $totalSynced;
    }
}