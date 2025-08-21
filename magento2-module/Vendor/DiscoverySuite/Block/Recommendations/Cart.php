<?php
/**
 * AI Product Discovery Suite - Cart Recommendations Block
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
use Magento\Checkout\Model\Session as CheckoutSession;
use Magento\Store\Model\StoreManagerInterface;
use Psr\Log\LoggerInterface;

class Cart extends Template
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
     * @var CheckoutSession
     */
    protected $checkoutSession;

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
     * @param CheckoutSession $checkoutSession
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
        CheckoutSession $checkoutSession,
        StoreManagerInterface $storeManager,
        LoggerInterface $logger,
        array $data = []
    ) {
        $this->discoveryHelper = $discoveryHelper;
        $this->customerSession = $customerSession;
        $this->productRepository = $productRepository;
        $this->searchCriteriaBuilder = $searchCriteriaBuilder;
        $this->checkoutSession = $checkoutSession;
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
     * Get cart cross-sell recommendations
     *
     * @return array
     */
    public function getCrossSellRecommendations()
    {
        if (!$this->isEnabled()) {
            return [];
        }

        try {
            $quote = $this->checkoutSession->getQuote();
            if (!$quote || !$quote->getItemsCount()) {
                return [];
            }

            $userId = $this->getUserId();
            $cartProductIds = [];
            $categoryIds = [];

            // Get products and categories from cart
            foreach ($quote->getAllVisibleItems() as $item) {
                $cartProductIds[] = (string)$item->getProductId();
                $product = $item->getProduct();
                if ($product && $product->getCategoryIds()) {
                    $categoryIds = array_merge($categoryIds, $product->getCategoryIds());
                }
            }

            $categoryIds = array_unique($categoryIds);
            
            // Get cart recommendations from API
            $apiUrl = $this->discoveryHelper->getServiceUrl('recommendation', '/api/v1/recommendations/');
            
            $client = new \Magento\Framework\HTTP\Client\Curl();
            $client->setHeaders([
                'Content-Type' => 'application/json',
                'User-Agent' => 'Magento-DiscoverySuite/1.0'
            ]);

            $requestData = [
                'user_id' => $userId,
                'context' => 'cart',
                'product_ids' => $cartProductIds,
                'category_ids' => array_map('strval', $categoryIds),
                'limit' => 6,
                'exclude_viewed' => false,
                'exclude_purchased' => false
            ];

            $client->post($apiUrl, json_encode($requestData));
            $response = $client->getBody();
            $data = json_decode($response, true);

            if (isset($data['recommendations']) && !empty($data['recommendations'])) {
                $recommendations = $this->loadProducts($data['recommendations']);
                
                // Filter out products already in cart
                return array_filter($recommendations, function($rec) use ($cartProductIds) {
                    return !in_array((string)$rec['product']->getId(), $cartProductIds);
                });
            }

        } catch (\Exception $e) {
            $this->logger->error('Cart Recommendations Error: ' . $e->getMessage());
        }

        return [];
    }

    /**
     * Get frequently bought together recommendations
     *
     * @return array
     */
    public function getFrequentlyBoughtTogether()
    {
        if (!$this->isEnabled()) {
            return [];
        }

        try {
            $quote = $this->checkoutSession->getQuote();
            if (!$quote || !$quote->getItemsCount()) {
                return [];
            }

            // Get the first product in cart as reference
            $firstItem = $quote->getAllVisibleItems()[0];
            $productId = $firstItem->getProductId();
            
            // Get similar products that are frequently bought together
            $apiUrl = $this->discoveryHelper->getServiceUrl('recommendation', '/api/v1/recommendations/similar');
            
            $client = new \Magento\Framework\HTTP\Client\Curl();
            $client->setHeaders([
                'Content-Type' => 'application/json',
                'User-Agent' => 'Magento-DiscoverySuite/1.0'
            ]);

            $requestData = [
                'product_id' => (string)$productId,
                'limit' => 4
            ];

            $client->post($apiUrl, json_encode($requestData));
            $response = $client->getBody();
            $data = json_decode($response, true);

            if (isset($data['recommendations']) && !empty($data['recommendations'])) {
                return $this->loadProducts($data['recommendations']);
            }

        } catch (\Exception $e) {
            $this->logger->error('Frequently Bought Together Error: ' . $e->getMessage());
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
                        'reason' => $rec['reason'] ?? 'Great with your cart items',
                        'algorithm' => $rec['metadata']['algorithm'] ?? 'cart_based'
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
        return 'discovery-cart-recommendations-' . uniqid();
    }

    /**
     * Get cart total for display
     *
     * @return float
     */
    public function getCartTotal()
    {
        try {
            $quote = $this->checkoutSession->getQuote();
            return $quote ? $quote->getGrandTotal() : 0;
        } catch (\Exception $e) {
            return 0;
        }
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
