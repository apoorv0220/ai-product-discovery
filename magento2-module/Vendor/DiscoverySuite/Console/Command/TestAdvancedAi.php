<?php
/**
 * DiscoverySuite Advanced AI Test Command
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
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Helper\Table;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Api\SearchInterface;
use Vendor\DiscoverySuite\Api\RecommendationInterface;
use Vendor\DiscoverySuite\Api\AssistantInterface;
use Vendor\DiscoverySuite\Model\Api\HttpClient;

class TestAdvancedAi extends Command
{
    /**
     * @var Data
     */
    private $helper;

    /**
     * @var SearchInterface
     */
    private $searchService;

    /**
     * @var RecommendationInterface
     */
    private $recommendationService;

    /**
     * @var AssistantInterface
     */
    private $assistantService;

    /**
     * @var HttpClient
     */
    private $httpClient;

    /**
     * Constructor
     */
    public function __construct(
        Data $helper,
        SearchInterface $searchService,
        RecommendationInterface $recommendationService,
        AssistantInterface $assistantService,
        HttpClient $httpClient,
        string $name = null
    ) {
        $this->helper = $helper;
        $this->searchService = $searchService;
        $this->recommendationService = $recommendationService;
        $this->assistantService = $assistantService;
        $this->httpClient = $httpClient;
        parent::__construct($name);
    }

    /**
     * Configure command
     */
    protected function configure()
    {
        $this->setName('discovery:test:advanced-ai')
            ->setDescription('Test Advanced AI Features Connectivity and Functionality')
            ->addOption(
                'feature',
                'f',
                InputOption::VALUE_OPTIONAL,
                'Test specific feature (search, recommendations, assistant, all)',
                'all'
            )
            ->addOption(
                'detailed',
                'd',
                InputOption::VALUE_NONE,
                'Show detailed test results'
            );
    }

    /**
     * Execute command
     */
    protected function execute(InputInterface $input, OutputInterface $output)
    {
        $feature = $input->getOption('feature');
        $detailed = $input->getOption('detailed');

        $output->writeln('<info>🚀 Testing Advanced AI Features</info>');
        $output->writeln('<info>=====================================</info>');
        $output->writeln('');

        // Test module status
        $this->testModuleStatus($output);

        // Test specific features
        $results = [];
        switch ($feature) {
            case 'search':
                $results['search'] = $this->testSearchFeatures($output, $detailed);
                break;
            case 'recommendations':
                $results['recommendations'] = $this->testRecommendationFeatures($output, $detailed);
                break;
            case 'assistant':
                $results['assistant'] = $this->testAssistantFeatures($output, $detailed);
                break;
            case 'all':
            default:
                $results['search'] = $this->testSearchFeatures($output, $detailed);
                $results['recommendations'] = $this->testRecommendationFeatures($output, $detailed);
                $results['assistant'] = $this->testAssistantFeatures($output, $detailed);
                break;
        }

        // Summary
        $this->showSummary($output, $results);

        return Command::SUCCESS;
    }

    /**
     * Test module status
     */
    private function testModuleStatus(OutputInterface $output)
    {
        $output->writeln('<comment>📋 Module Configuration Status:</comment>');

        $table = new Table($output);
        $table->setHeaders(['Feature', 'Status', 'Advanced Features']);

        $features = [
            ['Main Module', $this->helper->isEnabled() ? '✅ Enabled' : '❌ Disabled', ''],
            ['Search Service', $this->helper->isSearchEnabled() ? '✅ Enabled' : '❌ Disabled', 
                $this->getSearchFeatureStatus()],
            ['Recommendations', $this->helper->isRecommendationsEnabled() ? '✅ Enabled' : '❌ Disabled',
                $this->getRecommendationFeatureStatus()],
            ['Shopping Assistant', $this->helper->isShoppingAssistantEnabled() ? '✅ Enabled' : '❌ Disabled',
                $this->getAssistantFeatureStatus()],
            ['Analytics', $this->helper->isAnalyticsEnabled() ? '✅ Enabled' : '❌ Disabled',
                $this->getAnalyticsFeatureStatus()]
        ];

        $table->setRows($features);
        $table->render();
        $output->writeln('');
    }

    /**
     * Test search features
     */
    private function testSearchFeatures(OutputInterface $output, bool $detailed): array
    {
        $output->writeln('<comment>🔍 Testing Advanced Search Features:</comment>');
        $results = [];

        // Test 1: NLP-Enhanced Search
        $output->writeln('Testing NLP semantic search...');
        try {
            // First check if service is available
            if (!$this->helper->isServiceAvailable('search')) {
                $output->writeln('⚠️  Search service not available - testing fallback mode');
                $searchResult = $this->helper->getFallbackSearchResults('I want to buy a Hero Hoodie', 5);
                $results['nlp_search'] = ['status' => 'service_unavailable', 'fallback' => true];
            } else {
                $searchResult = $this->searchService->search('I want to buy a Hero Hoodie', 5);
            }
            
            if (!empty($searchResult['results'])) {
                $nlpEnabled = $searchResult['search_metadata']['nlp_enabled'] ?? false;
                $semanticSearch = $searchResult['search_metadata']['semantic_search'] ?? false;
                
                $output->writeln(sprintf(
                    '✅ NLP Search: %d results, NLP: %s, Semantic: %s',
                    count($searchResult['results']),
                    $nlpEnabled ? 'Yes' : 'No',
                    $semanticSearch ? 'Yes' : 'No'
                ));
                
                $results['nlp_search'] = [
                    'status' => 'success',
                    'results_count' => count($searchResult['results']),
                    'nlp_enabled' => $nlpEnabled,
                    'semantic_search' => $semanticSearch
                ];

                if ($detailed && isset($searchResult['ai_message'])) {
                    $output->writeln('   AI Message: ' . $searchResult['ai_message']);
                }
            } else {
                $output->writeln('⚠️  NLP Search: No results returned');
                $results['nlp_search'] = ['status' => 'no_results'];
            }
        } catch (\Exception $e) {
            $output->writeln('❌ NLP Search failed: ' . $e->getMessage());
            $results['nlp_search'] = ['status' => 'error', 'error' => $e->getMessage()];
        }

        // Test 2: Typo Tolerance
        $output->writeln('Testing typo tolerance...');
        try {
            $autocompleteResult = $this->searchService->autocomplete('Hro Hoodie', 5);
            
            if (!empty($autocompleteResult['suggestions'])) {
                $nlpProcessing = $autocompleteResult['ai_metadata']['nlp_processing'] ?? false;
                $typoCorrections = $autocompleteResult['ai_metadata']['typo_corrections'] ?? 0;
                
                $output->writeln(sprintf(
                    '✅ Typo Tolerance: %d suggestions, NLP: %s, Corrections: %d',
                    count($autocompleteResult['suggestions']),
                    $nlpProcessing ? 'Yes' : 'No',
                    $typoCorrections
                ));
                
                $results['typo_tolerance'] = [
                    'status' => 'success',
                    'suggestions_count' => count($autocompleteResult['suggestions']),
                    'nlp_processing' => $nlpProcessing,
                    'typo_corrections' => $typoCorrections
                ];
            } else {
                $output->writeln('⚠️  Typo Tolerance: No suggestions returned');
                $results['typo_tolerance'] = ['status' => 'no_results'];
            }
        } catch (\Exception $e) {
            $output->writeln('❌ Typo Tolerance failed: ' . $e->getMessage());
            $results['typo_tolerance'] = ['status' => 'error', 'error' => $e->getMessage()];
        }

        $output->writeln('');
        return $results;
    }

    /**
     * Test recommendation features
     */
    private function testRecommendationFeatures(OutputInterface $output, bool $detailed): array
    {
        $output->writeln('<comment>🤖 Testing ML-Powered Recommendations:</comment>');
        $results = [];

        // Test ML Recommendations
        $output->writeln('Testing ML-powered personalized recommendations...');
        try {
            $recommendations = $this->recommendationService->getRecommendations('test_user_ml', 'homepage', 5);
            
            if (!empty($recommendations['recommendations'])) {
                $mlPowered = $recommendations['ml_insights']['ml_powered'] ?? false;
                $personalized = $recommendations['ml_insights']['personalized'] ?? false;
                $algorithms = $recommendations['ml_insights']['algorithms_used'] ?? [];
                
                $output->writeln(sprintf(
                    '✅ ML Recommendations: %d items, ML: %s, Personalized: %s',
                    count($recommendations['recommendations']),
                    $mlPowered ? 'Yes' : 'No',
                    $personalized ? 'Yes' : 'No'
                ));
                
                if ($detailed && !empty($algorithms)) {
                    $output->writeln('   Algorithms: ' . implode(', ', $algorithms));
                }
                
                $results['ml_recommendations'] = [
                    'status' => 'success',
                    'count' => count($recommendations['recommendations']),
                    'ml_powered' => $mlPowered,
                    'personalized' => $personalized,
                    'algorithms' => $algorithms
                ];
            } else {
                $output->writeln('⚠️  ML Recommendations: No recommendations returned');
                $results['ml_recommendations'] = ['status' => 'no_results'];
            }
        } catch (\Exception $e) {
            $output->writeln('❌ ML Recommendations failed: ' . $e->getMessage());
            $results['ml_recommendations'] = ['status' => 'error', 'error' => $e->getMessage()];
        }

        // Test Real-time Learning
        $output->writeln('Testing real-time learning interaction recording...');
        try {
            $recorded = $this->assistantService->recordInteraction('test_user', 'test_product', 'view', [
                'source' => 'testing',
                'timestamp' => date('c')
            ]);
            
            if ($recorded) {
                $output->writeln('✅ Real-time Learning: Interaction recorded successfully');
                $results['real_time_learning'] = ['status' => 'success'];
            } else {
                $output->writeln('⚠️  Real-time Learning: Recording may have failed');
                $results['real_time_learning'] = ['status' => 'warning'];
            }
        } catch (\Exception $e) {
            $output->writeln('❌ Real-time Learning failed: ' . $e->getMessage());
            $results['real_time_learning'] = ['status' => 'error', 'error' => $e->getMessage()];
        }

        $output->writeln('');
        return $results;
    }

    /**
     * Test assistant features
     */
    private function testAssistantFeatures(OutputInterface $output, bool $detailed): array
    {
        $output->writeln('<comment>💬 Testing Conversational AI Assistant:</comment>');
        $results = [];

        // Test Conversational AI
        $output->writeln('Testing conversational AI chat...');
        try {
            $chatResponse = $this->assistantService->chat(
                'Hi, I am looking for a good hoodie',
                'test_session_' . time(),
                'test_user'
            );
            
            if (!empty($chatResponse['message'])) {
                $aiPowered = $chatResponse['magento_integration']['ai_powered'] ?? false;
                $nlpProcessing = $chatResponse['magento_integration']['nlp_processing'] ?? false;
                $contextAware = $chatResponse['magento_integration']['context_aware'] ?? false;
                
                $output->writeln(sprintf(
                    '✅ Conversational AI: Response received, AI: %s, NLP: %s, Context: %s',
                    $aiPowered ? 'Yes' : 'No',
                    $nlpProcessing ? 'Yes' : 'No',
                    $contextAware ? 'Yes' : 'No'
                ));
                
                if ($detailed) {
                    $output->writeln('   Response: ' . substr($chatResponse['message'], 0, 100) . '...');
                    if (!empty($chatResponse['suggested_actions'])) {
                        $output->writeln('   Suggested Actions: ' . count($chatResponse['suggested_actions']));
                    }
                }
                
                $results['conversational_ai'] = [
                    'status' => 'success',
                    'ai_powered' => $aiPowered,
                    'nlp_processing' => $nlpProcessing,
                    'context_aware' => $contextAware,
                    'message_length' => strlen($chatResponse['message']),
                    'suggested_actions' => count($chatResponse['suggested_actions'] ?? [])
                ];
            } else {
                $output->writeln('⚠️  Conversational AI: No response received');
                $results['conversational_ai'] = ['status' => 'no_response'];
            }
        } catch (\Exception $e) {
            $output->writeln('❌ Conversational AI failed: ' . $e->getMessage());
            $results['conversational_ai'] = ['status' => 'error', 'error' => $e->getMessage()];
        }

        $output->writeln('');
        return $results;
    }

    /**
     * Show test summary
     */
    private function showSummary(OutputInterface $output, array $results)
    {
        $output->writeln('<info>📊 Test Summary:</info>');
        $output->writeln('<info>================</info>');

        $totalTests = 0;
        $passedTests = 0;

        foreach ($results as $category => $tests) {
            foreach ($tests as $test => $result) {
                $totalTests++;
                if ($result['status'] === 'success') {
                    $passedTests++;
                }
            }
        }

        $successRate = $totalTests > 0 ? round(($passedTests / $totalTests) * 100) : 0;

        $output->writeln(sprintf('Total Tests: %d', $totalTests));
        $output->writeln(sprintf('Passed: %d', $passedTests));
        $output->writeln(sprintf('Success Rate: %d%%', $successRate));
        $output->writeln('');

        if ($successRate >= 80) {
            $output->writeln('<info>🎉 Advanced AI features are working excellently!</info>');
        } elseif ($successRate >= 60) {
            $output->writeln('<comment>⚠️  Most AI features are working, some may need attention.</comment>');
        } else {
            $output->writeln('<error>❌ Several AI features need troubleshooting.</error>');
        }

        $output->writeln('');
        $output->writeln('<comment>💡 Test your AI-powered store:</comment>');
        $output->writeln('• Try searching: "I want to buy a comfortable hoodie"');
        $output->writeln('• Test typos: "Hro Hoddie" or "Aple Phne"');
        $output->writeln('• Check recommendations on product pages');
        $output->writeln('• Use the AI chat assistant');
    }

    /**
     * Get search feature status
     */
    private function getSearchFeatureStatus(): string
    {
        $features = [];
        if ($this->helper->isNlpEnabled()) $features[] = 'NLP';
        if ($this->helper->isTypoToleranceEnabled()) $features[] = 'Typo Tolerance';
        if ($this->helper->isIntentRecognitionEnabled()) $features[] = 'Intent Recognition';
        if ($this->helper->isSemanticSearchEnabled()) $features[] = 'Semantic Search';
        
        return implode(', ', $features) ?: 'Basic';
    }

    /**
     * Get recommendation feature status
     */
    private function getRecommendationFeatureStatus(): string
    {
        $features = [];
        if ($this->helper->isMlPoweredRecommendationsEnabled()) $features[] = 'ML-Powered';
        if ($this->helper->isRealTimeLearningEnabled()) $features[] = 'Real-time Learning';
        if ($this->helper->isCollaborativeFilteringEnabled()) $features[] = 'Collaborative Filtering';
        if ($this->helper->isContentBasedEnabled()) $features[] = 'Content-based';
        
        return implode(', ', $features) ?: 'Basic';
    }

    /**
     * Get assistant feature status
     */
    private function getAssistantFeatureStatus(): string
    {
        $features = [];
        if ($this->helper->isConversationalAiEnabled()) $features[] = 'Conversational AI';
        if ($this->helper->isChatNlpEnabled()) $features[] = 'NLP Processing';
        if ($this->helper->isMultiTurnConversationsEnabled()) $features[] = 'Multi-turn';
        
        return implode(', ', $features) ?: 'Basic';
    }

    /**
     * Get analytics feature status
     */
    private function getAnalyticsFeatureStatus(): string
    {
        $features = [];
        if ($this->helper->isRealTimeTrackingEnabled()) $features[] = 'Real-time Tracking';
        if ($this->helper->isBehavioralInsightsEnabled()) $features[] = 'Behavioral Insights';
        if ($this->helper->isAbTestingEnabled()) $features[] = 'A/B Testing';
        if ($this->helper->isPredictiveAnalyticsEnabled()) $features[] = 'Predictive Analytics';
        
        return implode(', ', $features) ?: 'Basic';
    }
}
