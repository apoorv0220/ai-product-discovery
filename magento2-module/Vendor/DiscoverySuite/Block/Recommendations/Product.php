<?php
/**
 * AI Product Discovery Suite - Product Page Recommendations Block
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Block\Recommendations;

use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Vendor\DiscoverySuite\Helper\Data as DiscoveryHelper;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Catalog\Model\ProductRepository;
use Magento\Framework\Api\SearchCriteriaBuilder;
use Magento\Framework\Registry;
use Magento\Store\Model\StoreManagerInterface;
use Psr\Log\LoggerInterface;

class Product extends Template
{
    /**
     * @var DiscoveryHelper
     */
    protected $discoveryHelper;

    /**
     * @var CustomerSession
     */
    protected $customerSession;

    /**
     * @var ProductRepository
     */
    protected $productRepository;

    /**
     * @var SearchCriteriaBuilder
     */
    protected $searchCriteriaBuilder;

    /**
     * @var Registry
     */
    protected $registry;

    /**
     * @var StoreManagerInterface
     */
    protected $storeManager;

    /**
     * @var LoggerInterface
     */
    protected $logger;

    /**
     * @param Context $context
     * @param DiscoveryHelper $discoveryHelper
     * @param CustomerSession $customerSession
     * @param ProductRepository $productRepository
     * @param SearchCriteriaBuilder $searchCriteriaBuilder
     * @param Registry $registry
     * @param StoreManagerInterface $storeManager
     * @param LoggerInterface $logger
     * @param array $data
     */
    public function __construct(
        Context $context,
        DiscoveryHelper $discoveryHelper,
        CustomerSession $customerSession,
        ProductRepository $productRepository,
        SearchCriteriaBuilder $searchCriteriaBuilder,
        Registry $registry,
        StoreManagerInterface $storeManager,
        LoggerInterface $logger,
        array $data = []
    ) {
        $this->discoveryHelper = $discoveryHelper;
        $this->customerSession = $customerSession;
        $this->productRepository = $productRepository;
        $this->searchCriteriaBuilder = $searchCriteriaBuilder;
        $this->registry = $registry;
        $this->storeManager = $storeManager;
        $this->logger = $logger;
        parent::__construct($context, $data);
    }

    /**
     * Check if recommendations are enabled
     *
     * @return bool
     */
    public function isEnabled()
    {
        return $this->discoveryHelper->isEnabled() && $this->discoveryHelper->isRecommendationsEnabled();
    }

    /**
     * Get current product
     *
     * @return \Magento\Catalog\Model\Product|null
     */
    public function getCurrentProduct()
    {
        return $this->registry->registry('current_product');
    }

    /**
     * Get similar products recommendations
     *
     * @return array
     */
    public function getSimilarProducts()
    {
        if (!$this->isEnabled()) {
            return [];
        }

        $currentProduct = $this->getCurrentProduct();
        if (!$currentProduct) {
            return [];
        }

        try {
            $productId = $currentProduct->getId();
            
            // Get similar products from API
            $apiUrl = $this->discoveryHelper->getServiceUrl('recommendation', '/api/v1/recommendations/similar');
            
            $client = new \Magento\Framework\HTTP\Client\Curl();
            $client->setHeaders([
                'Content-Type' => 'application/json',
                'User-Agent' => 'Magento-DiscoverySuite/1.0'
            ]);

            $requestData = [
                'product_id' => (string)$productId,
                'limit' => 6
            ];

            $client->post($apiUrl, json_encode($requestData));
            $response = $client->getBody();
            $data = json_decode($response, true);

            if (isset($data['recommendations']) && !empty($data['recommendations'])) {
                return $this->loadProducts($data['recommendations']);
            }

        } catch (\Exception $e) {
            $this->logger->error('Similar Products Error: ' . $e->getMessage());
        }

        return [];
    }

    /**
     * Get personalized product recommendations
     *
     * @return array
     */
    public function getPersonalizedRecommendations()
    {
        if (!$this->isEnabled()) {
            return [];
        }

        $currentProduct = $this->getCurrentProduct();
        if (!$currentProduct) {
            return [];
        }

        try {
            $userId = $this->getUserId();
            $productId = $currentProduct->getId();
            $categoryIds = $currentProduct->getCategoryIds();
            
            // Get personalized recommendations from API
            $apiUrl = $this->discoveryHelper->getServiceUrl('recommendation', '/api/v1/recommendations/');
            
            $client = new \Magento\Framework\HTTP\Client\Curl();
            $client->setHeaders([
                'Content-Type' => 'application/json',
                'User-Agent' => 'Magento-DiscoverySuite/1.0'
            ]);

            $requestData = [
                'user_id' => $userId,
                'context' => 'product_detail',
                'product_ids' => [(string)$productId],
                'category_ids' => array_map('strval', $categoryIds),
                'limit' => 4
            ];

            $client->post($apiUrl, json_encode($requestData));
            $response = $client->getBody();
            $data = json_decode($response, true);

            if (isset($data['recommendations']) && !empty($data['recommendations'])) {
                return $this->loadProducts($data['recommendations']);
            }

        } catch (\Exception $e) {
            $this->logger->error('Personalized Recommendations Error: ' . $e->getMessage());
        }

        return [];
    }

    /**
     * Get user ID for recommendations
     *
     * @return string
     */
    private function getUserId()
    {
        if ($this->customerSession->isLoggedIn()) {
            return 'customer_' . $this->customerSession->getCustomerId();
        }
        
        // Use session ID for anonymous users
        return 'guest_' . $this->customerSession->getSessionId();
    }

    /**
     * Load Magento products from recommendations
     *
     * @param array $recommendations
     * @return array
     */
    private function loadProducts($recommendations)
    {
        $productIds = array_column($recommendations, 'product_id');
        
        if (empty($productIds)) {
            return [];
        }

        try {
            $searchCriteria = $this->searchCriteriaBuilder
                ->addFilter('entity_id', $productIds, 'in')
                ->addFilter('status', 1)
                ->addFilter('visibility', [2, 3, 4], 'in')
                ->create();

            $products = $this->productRepository->getList($searchCriteria)->getItems();
            
            $result = [];
            foreach ($recommendations as $rec) {
                $productId = $rec['product_id'];
                if (isset($products[$productId])) {
                    $product = $products[$productId];
                    $result[] = [
                        'product' => $product,
                        'score' => $rec['score'] ?? 0,
                        'reason' => $rec['reason'] ?? 'Similar product',
                        'algorithm' => $rec['metadata']['algorithm'] ?? 'content_based',
                        'similarity_score' => $rec['metadata']['similarity_score'] ?? $rec['score'] ?? 0
                    ];
                }
            }

            return $result;

        } catch (\Exception $e) {
            $this->logger->error('Load Products Error: ' . $e->getMessage());
            return [];
        }
    }

    /**
     * Get recommendation tracking URL
     *
     * @return string
     */
    public function getTrackingUrl()
    {
        return $this->getUrl('discovery/recommendations/track');
    }

    /**
     * Get unique block ID
     *
     * @return string
     */
    public function getBlockId()
    {
        return 'discovery-product-recommendations-' . uniqid();
    }
    
    /**
     * Get product price HTML
     *
     * @param \Magento\Catalog\Model\Product $product
     * @return string
     */
    public function getProductPrice($product)
    {
        return $this->getLayout()->createBlock('Magento\Framework\Pricing\Render')
            ->render(
                'final_price',
                $product,
                [
                    'price_id' => 'old-price-' . $product->getId() . '-' . $this->getRandomString(4),
                    'display_minimal_price' => true,
                    'include_container' => true,
                    'zone' => 'item_list'
                ]
            );
    }
    
    /**
     * Get product image
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param string $imageId
     * @return \Magento\Catalog\Block\Product\Image
     */
    public function getImage($product, $imageId)
    {
        $imageHelper = $this->_objectManager->get('\Magento\Catalog\Helper\Image');
        return $imageHelper->init($product, $imageId);
    }
    
    /**
     * Get product image URL
     *
     * @param \Magento\Catalog\Model\Product $product
     * @param string $imageId
     * @return string
     */
    public function getProductImageUrl($product, $imageId = 'product_page_image_small')
    {
        try {
            // Try to get the actual image URL from product
            $storeManager = $this->_objectManager->get('\Magento\Store\Model\StoreManagerInterface');
            $baseUrl = $storeManager->getStore()->getBaseUrl(\Magento\Framework\UrlInterface::URL_TYPE_MEDIA);
            
            // Get the image from product data
            $imagePath = null;
            if ($product->getSmallImage() && $product->getSmallImage() !== 'no_selection') {
                $imagePath = $product->getSmallImage();
            } elseif ($product->getImage() && $product->getImage() !== 'no_selection') {
                $imagePath = $product->getImage();
            } elseif ($product->getThumbnail() && $product->getThumbnail() !== 'no_selection') {
                $imagePath = $product->getThumbnail();
            }
            
            if ($imagePath) {
                return $baseUrl . 'catalog/product' . $imagePath;
            }
            
            // Fallback to image helper
            $imageHelper = $this->_objectManager->get('\Magento\Catalog\Helper\Image');
            return $imageHelper->init($product, $imageId)->getUrl();
            
        } catch (\Exception $e) {
            // Fallback to placeholder image
            return $this->getViewFileUrl('Magento_Catalog::images/product/placeholder/small_image.jpg');
        }
    }
    
    /**
     * Generate random string
     *
     * @param int $length
     * @return string
     */
    private function getRandomString($length = 4)
    {
        return substr(str_shuffle('0123456789abcdefghijklmnopqrstuvwxyz'), 0, $length);
    }
}
