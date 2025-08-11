<?php
/**
 * DiscoverySuite Recommendations Widget Block
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Block\Recommendations;

use Vendor\DiscoverySuite\Api\RecommendationInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Catalog\Api\ProductRepositoryInterface;
use Magento\Framework\Json\Helper\Data as JsonHelper;
use Magento\Framework\Registry;

class Widget extends Template
{
    /**
     * @var RecommendationInterface
     */
    private $recommendationService;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * @var ProductRepositoryInterface
     */
    private $productRepository;

    /**
     * @var JsonHelper
     */
    private $jsonHelper;

    /**
     * @var Registry
     */
    private $registry;

    /**
     * Constructor
     *
     * @param Context $context
     * @param RecommendationInterface $recommendationService
     * @param Data $helper
     * @param CustomerSession $customerSession
     * @param ProductRepositoryInterface $productRepository
     * @param JsonHelper $jsonHelper
     * @param Registry $registry
     * @param array $data
     */
    public function __construct(
        Context $context,
        RecommendationInterface $recommendationService,
        Data $helper,
        CustomerSession $customerSession,
        ProductRepositoryInterface $productRepository,
        JsonHelper $jsonHelper,
        Registry $registry,
        array $data = []
    ) {
        $this->recommendationService = $recommendationService;
        $this->helper = $helper;
        $this->customerSession = $customerSession;
        $this->productRepository = $productRepository;
        $this->jsonHelper = $jsonHelper;
        $this->registry = $registry;
        parent::__construct($context, $data);
    }

    /**
     * Check if recommendations are enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->helper->isRecommendationsEnabled();
    }

    /**
     * Get recommendations for current context
     *
     * @return array
     */
    public function getRecommendations(): array
    {
        if (!$this->isEnabled()) {
            return [];
        }

        try {
            $userId = $this->getUserId();
            $context = $this->getRecommendationContext();
            $limit = (int) $this->getData('limit') ?: 12;

            $recommendations = $this->recommendationService->getRecommendations(
                $userId,
                $context,
                $limit
            );

            return $this->loadProductDetails($recommendations);

        } catch (\Exception $e) {
            $this->_logger->error('Recommendations loading failed', [
                'context' => $this->getRecommendationContext(),
                'error' => $e->getMessage()
            ]);
            return [];
        }
    }

    /**
     * Get similar products for current product
     *
     * @return array
     */
    public function getSimilarProducts(): array
    {
        if (!$this->isEnabled()) {
            return [];
        }

        $currentProduct = $this->registry->registry('current_product');
        if (!$currentProduct) {
            return [];
        }

        try {
            $limit = (int) $this->getData('limit') ?: 12;
            $similarProducts = $this->recommendationService->getSimilarProducts(
                (int) $currentProduct->getId(),
                $limit
            );

            return $this->loadProductDetails($similarProducts);

        } catch (\Exception $e) {
            $this->_logger->error('Similar products loading failed', [
                'product_id' => $currentProduct->getId(),
                'error' => $e->getMessage()
            ]);
            return [];
        }
    }

    /**
     * Get widget configuration as JSON
     *
     * @return string
     */
    public function getConfigJson(): string
    {
        $config = [
            'enabled' => $this->isEnabled(),
            'userId' => $this->getUserId(),
            'context' => $this->getRecommendationContext(),
            'trackingEndpoint' => $this->getUrl('discovery/recommendations/track'),
            'limit' => (int) $this->getData('limit') ?: 12
        ];

        return $this->jsonHelper->jsonEncode($config);
    }

    /**
     * Get user ID for recommendations
     *
     * @return string
     */
    private function getUserId(): string
    {
        if ($this->customerSession->isLoggedIn()) {
            return 'customer_' . $this->customerSession->getCustomerId();
        }

        return 'guest_' . $this->customerSession->getSessionId();
    }

    /**
     * Get recommendation context
     *
     * @return string
     */
    private function getRecommendationContext(): string
    {
        $context = $this->getData('context');
        
        if ($context) {
            return $context;
        }

        // Auto-detect context
        $currentProduct = $this->registry->registry('current_product');
        if ($currentProduct) {
            return 'product_view';
        }

        $currentCategory = $this->registry->registry('current_category');
        if ($currentCategory) {
            return 'category_view';
        }

        return 'homepage';
    }

    /**
     * Load full product details for recommendations
     *
     * @param array $recommendations
     * @return array
     */
    private function loadProductDetails(array $recommendations): array
    {
        $products = [];

        foreach ($recommendations as $recommendation) {
            try {
                $productId = $recommendation['product_id'] ?? $recommendation['id'] ?? null;
                if ($productId) {
                    $product = $this->productRepository->getById($productId);
                    $products[] = [
                        'product' => $product,
                        'score' => $recommendation['score'] ?? 1.0,
                        'reason' => $recommendation['reason'] ?? ''
                    ];
                }
            } catch (\Exception $e) {
                // Skip products that can't be loaded
                continue;
            }
        }

        return $products;
    }

    /**
     * Get cache key info
     *
     * @return array
     */
    public function getCacheKeyInfo()
    {
        return [
            'DISCOVERY_RECOMMENDATIONS',
            $this->_storeManager->getStore()->getId(),
            $this->getUserId(),
            $this->getRecommendationContext(),
            $this->getData('limit') ?: 12
        ];
    }
}