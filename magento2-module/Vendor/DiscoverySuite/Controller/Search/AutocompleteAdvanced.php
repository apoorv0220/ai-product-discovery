<?php
/**
 * Advanced Autocomplete Controller with Required Keys
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 */

namespace Vendor\DiscoverySuite\Controller\Search;

use Magento\Framework\App\Action\Action;
use Magento\Framework\App\Action\Context;
use Magento\Framework\Controller\Result\JsonFactory;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Api\SearchInterface;
use Magento\Catalog\Model\ResourceModel\Product\CollectionFactory;
use Magento\Store\Model\StoreManagerInterface;
use Magento\Catalog\Helper\Image;
use Psr\Log\LoggerInterface;

class AutocompleteAdvanced extends Action
{
    /**
     * @var JsonFactory
     */
    private $jsonFactory;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var SearchInterface
     */
    private $searchService;

    /**
     * @var CollectionFactory
     */
    private $productCollectionFactory;

    /**
     * @var StoreManagerInterface
     */
    private $storeManager;

    /**
     * @var Image
     */
    private $imageHelper;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     */
    public function __construct(
        Context $context,
        JsonFactory $jsonFactory,
        Data $helper,
        SearchInterface $searchService,
        CollectionFactory $productCollectionFactory,
        StoreManagerInterface $storeManager,
        Image $imageHelper,
        LoggerInterface $logger
    ) {
        $this->jsonFactory = $jsonFactory;
        $this->helper = $helper;
        $this->searchService = $searchService;
        $this->productCollectionFactory = $productCollectionFactory;
        $this->storeManager = $storeManager;
        $this->imageHelper = $imageHelper;
        $this->logger = $logger;
        parent::__construct($context);
    }

    /**
     * Execute autocomplete action
     */
    public function execute()
    {
        $result = $this->jsonFactory->create();
        
        try {
            $query = $this->getRequest()->getParam('q', '');
            $limit = (int)$this->getRequest()->getParam('limit', 10);

            if (empty($query) || strlen($query) < 2) {
                return $result->setData(['suggestions' => []]);
            }

            // Try AI-powered autocomplete first
            $suggestions = $this->getAiSuggestions($query, $limit);
            
            // If AI fails, use fallback
            if (empty($suggestions)) {
                $suggestions = $this->getFallbackSuggestions($query, $limit);
            }

            return $result->setData([
                'suggestions' => $suggestions,
                'query' => $query
            ]);

        } catch (\Exception $e) {
            $this->logger->error('DiscoverySuite Autocomplete Error: ' . $e->getMessage());
            
            // Return fallback on error
            $suggestions = $this->getFallbackSuggestions($query ?? '', $limit ?? 10);
            return $result->setData([
                'suggestions' => $suggestions,
                'query' => $query ?? '',
                'error' => 'Fallback mode active'
            ]);
        }
    }

    /**
     * Get AI-powered suggestions
     */
    private function getAiSuggestions(string $query, int $limit): array
    {
        try {
            if (!$this->helper->isServiceAvailable('search')) {
                return [];
            }

            $aiResponse = $this->searchService->autocomplete($query, $limit);
            
            if (empty($aiResponse) || !isset($aiResponse['suggestions'])) {
                return [];
            }

            return $this->formatSuggestions($aiResponse['suggestions']);

        } catch (\Exception $e) {
            $this->logger->warning('AI autocomplete failed: ' . $e->getMessage());
            return [];
        }
    }

    /**
     * Get fallback suggestions from Magento
     */
    private function getFallbackSuggestions(string $query, int $limit): array
    {
        try {
            $collection = $this->productCollectionFactory->create();
            $collection->addAttributeToSelect(['name', 'price', 'image', 'url_key'])
                      ->addAttributeToFilter('status', 1)
                      ->addAttributeToFilter('visibility', ['in' => [2, 3, 4]])
                      ->addAttributeToFilter('name', ['like' => '%' . $query . '%'])
                      ->setPageSize($limit)
                      ->load();

            $suggestions = [];
            $store = $this->storeManager->getStore();
            
            foreach ($collection as $product) {
                $suggestions[] = [
                    'title' => $product->getName(),
                    'image' => $this->getProductImageUrl($product),
                    'price' => $this->formatPrice($product->getPrice()),
                    'url' => $product->getProductUrl(),
                    'category' => $this->getProductCategory($product),
                    'type' => 'product',
                    'sku' => $product->getSku(),
                    'id' => $product->getId(),
                    'fallback' => true
                ];
            }

            return $suggestions;

        } catch (\Exception $e) {
            $this->logger->error('Fallback autocomplete failed: ' . $e->getMessage());
            return [];
        }
    }

    /**
     * Format AI suggestions to required format
     */
    private function formatSuggestions(array $aiSuggestions): array
    {
        $formatted = [];
        
        foreach ($aiSuggestions as $suggestion) {
            $formatted[] = [
                'title' => $suggestion['suggestion'] ?? $suggestion['title'] ?? '',
                'image' => $suggestion['image'] ?? $this->getDefaultImage(),
                'price' => $suggestion['price'] ?? '$0.00',
                'url' => $suggestion['url'] ?? '#',
                'category' => $suggestion['category'] ?? 'General',
                'type' => $suggestion['type'] ?? 'product',
                'sku' => $suggestion['sku'] ?? '',
                'id' => $suggestion['id'] ?? 0,
                'ai_enhanced' => true,
                'confidence' => $suggestion['confidence'] ?? 1.0
            ];
        }

        return $formatted;
    }

    /**
     * Get product image URL
     */
    private function getProductImageUrl($product): string
    {
        try {
            return $this->imageHelper->init($product, 'product_page_image_small')->getUrl();
        } catch (\Exception $e) {
            return $this->getDefaultImage();
        }
    }

    /**
     * Get default image URL
     */
    private function getDefaultImage(): string
    {
        return $this->storeManager->getStore()->getBaseUrl(\Magento\Framework\UrlInterface::URL_TYPE_MEDIA) 
               . 'catalog/product/placeholder/default/placeholder.jpg';
    }

    /**
     * Format price
     */
    private function formatPrice($price): string
    {
        return '$' . number_format((float)$price, 2);
    }

    /**
     * Get product category
     */
    private function getProductCategory($product): string
    {
        try {
            $categories = $product->getCategoryIds();
            if (!empty($categories)) {
                $objectManager = \Magento\Framework\App\ObjectManager::getInstance();
                $category = $objectManager->create('Magento\Catalog\Model\Category')->load($categories[0]);
                return $category->getName();
            }
            return 'General';
        } catch (\Exception $e) {
            return 'General';
        }
    }
}
