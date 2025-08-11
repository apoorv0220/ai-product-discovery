<?php
/**
 * DiscoverySuite Reindex Search Console Command
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

class ReindexSearch extends Command
{
    const STORE_ID = 'store-id';
    const FORCE = 'force';

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
        $this->setName('discovery:reindex:search')
            ->setDescription('Reindex search data in AI Discovery Suite')
            ->addOption(
                self::STORE_ID,
                's',
                InputOption::VALUE_OPTIONAL,
                'Store ID to reindex',
                1
            )
            ->addOption(
                self::FORCE,
                'f',
                InputOption::VALUE_NONE,
                'Force reindex even if data is up to date'
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
            
            $storeId = (int)$input->getOption(self::STORE_ID);
            $force = $input->getOption(self::FORCE);

            $output->writeln('<info>Starting search reindex...</info>');
            $output->writeln("Store ID: {$storeId}");
            $output->writeln("Force reindex: " . ($force ? 'Yes' : 'No'));

            if (!$this->helper->isEnabled()) {
                $output->writeln('<error>Discovery Suite is not enabled. Please enable it in configuration.</error>');
                return Command::FAILURE;
            }

            // Test API connection first
            $output->writeln('<info>Testing search service connection...</info>');
            $isConnected = $this->testSearchService($output);
            
            if (!$isConnected) {
                $output->writeln('<error>Search service connection failed. Please check your configuration.</error>');
                return Command::FAILURE;
            }

            $output->writeln('<info>Search service connection successful!</info>');

            // Clear existing index if force is enabled
            if ($force) {
                $output->writeln('<info>Clearing existing search index...</info>');
                $this->clearSearchIndex($output);
            }

            // Reindex search data
            $reindexedCount = $this->reindexSearchData($storeId, $output);

            $output->writeln("<info>Search reindex completed successfully! Reindexed {$reindexedCount} items.</info>");
            return Command::SUCCESS;

        } catch (\Exception $e) {
            $output->writeln('<error>Error during search reindex: ' . $e->getMessage() . '</error>');
            return Command::FAILURE;
        }
    }

    /**
     * Test search service connection
     *
     * @param OutputInterface $output
     * @return bool
     */
    private function testSearchService(OutputInterface $output): bool
    {
        try {
            $searchEndpoint = $this->helper->getApiBaseUrl() . ':' . $this->helper->getSearchServicePort() . '/health/';
            $response = $this->httpClient->get($searchEndpoint);
            
            if (!empty($response['status']) && $response['status'] === 'healthy') {
                return true;
            }
            
            return false;
        } catch (\Exception $e) {
            $output->writeln('<comment>Search service test failed: ' . $e->getMessage() . '</comment>');
            return false;
        }
    }

    /**
     * Clear search index
     *
     * @param OutputInterface $output
     * @return bool
     */
    private function clearSearchIndex(OutputInterface $output): bool
    {
        try {
            // This would call the search service to clear the index
            $output->writeln('<comment>Index clearing functionality to be implemented.</comment>');
            return true;
        } catch (\Exception $e) {
            $output->writeln('<error>Failed to clear search index: ' . $e->getMessage() . '</error>');
            return false;
        }
    }

    /**
     * Reindex search data
     *
     * @param int $storeId
     * @param OutputInterface $output
     * @return int
     */
    private function reindexSearchData(int $storeId, OutputInterface $output): int
    {
        $reindexedCount = 0;
        
        // This is a placeholder - in a real implementation, you would:
        // 1. Load products, categories, and other searchable content
        // 2. Format them for the search index
        // 3. Send them to the search service
        // 4. Update search configurations and synonyms
        
        $output->writeln('<comment>Search reindex functionality to be implemented based on your search requirements.</comment>');
        $output->writeln('<comment>This command will reindex data for: ' . $this->helper->getApiBaseUrl() . ':' . $this->helper->getSearchServicePort() . '/api/v1/index/</comment>');
        
        return $reindexedCount;
    }
}