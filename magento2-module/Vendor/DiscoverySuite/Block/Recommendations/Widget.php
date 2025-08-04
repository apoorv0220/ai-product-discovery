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

use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;
use Magento\Framework\Serialize\Serializer\Json;
use Vendor\DiscoverySuite\Api\RecommendationInterface;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Catalog\Model\ProductRepository;
use Magento\Framework\Registry;

class Widget extends Template
{
    /**
     * @var ScopeConfigInterface
     */
    private $scopeConfig;

    /**
     * @var Json
     */
    private $jsonSerializer;

    /**
     * @var RecommendationInterface
     */
    private $recommendationService;

    /**
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * @var ProductRepository
     */
    private $productRepository;

    /**
     * @var Registry
     */
    private $registry;

    /**
     * Configuration paths
     */
    const XML_PATH_RECOMMENDATIONS_ENABLED = 'discovery_suite/recommendations/enabled';

    /**
     * @param Context $context
     * @param ScopeConfigInterface $scopeConfig
     * @param Json $jsonSerializer
     * @param RecommendationInterface $recommendationService
     * @param CustomerSession $customerSession
     * @param ProductRepository $productRepository
     * @param Registry $registry
     * @param array $data
     */
    public function __construct(
        Context $context,
        ScopeConfigInterface $scopeConfig,
        Json $jsonSerializer,
        RecommendationInterface $recommendationService,
        CustomerSession $customerSession,
        ProductRepository $productRepository,
        Registry $registry,
        array $data = []
    ) {
        $this->scopeConfig = $scopeConfig;
        $this->jsonSerializer = $jsonSerializer;
        $this->recommendationService = $recommendationService;
        $this->customerSession = $customerSession;
        $this->productRepository = $productRepository;
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
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_RECOMMENDATIONS_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Get widget configuration
     *
     * @return string JSON encoded configuration
     */
    public function getWidgetConfig(): string
    {
        $config = [
            'enabled' => $this->isEnabled(),
            'context' => $this->getContext(),
            'limit' => $this->getLimit(),
            'layout' => $this->getLayout(),
            'url' => $this->getRecommendationUrl(),
            'trackingUrl' => $this->getTrackingUrl(),
            'productId' => $this->getCurrentProductId(),
            'customerId' => $this->customerSession->getCustomerId(),
            'storeId' => $this->_storeManager->getStore()->getId()
        ];

        return $this->jsonSerializer->serialize($config);
    }

    /**
     * Get recommendation context
     *
     * @return string
     */
    public function getContext(): string
    {
        return $this->getData('context') ?: 'homepage';
    }

    /**
     * Get recommendation limit
     *
     * @return int
     */
    public function getLimit(): int
    {
        return (int) $this->getData('limit') ?: 12;
    }

    /**
     * Get widget layout
     *
     * @return string
     */
    public function getLayout(): string
    {
        return $this->getData('layout') ?: 'grid';
    }

    /**
     * Get current product ID if on product page
     *
     * @return int|null
     */
    public function getCurrentProductId(): ?int
    {
        $product = $this->registry->registry('current_product');
        return $product ? (int) $product->getId() : null;
    }

    /**
     * Get recommendations
     *
     * @return array
     */
    public function getRecommendations(): array
    {
        if (!$this->isEnabled()) {
            return [];
        }

        try {
            $context = $this->getContext();
            $params = [];

            // Add context-specific parameters
            if ($context === 'product' && $this->getCurrentProductId()) {
                $params['product_id'] = $this->getCurrentProductId();
            }

            $recommendations = $this->recommendationService->getRecommendations(
                $context,
                $params,
                $this->customerSession->getCustomerId(),
                null,
                $this->getLimit()
            );

            return $recommendations['products'] ?? [];

        } catch (\Exception $e) {
            $this->_logger->error('Failed to get recommendations', [
                'context' => $this->getContext(),
                'error' => $e->getMessage()
            ]);

            return [];
        }
    }

    /**
     * Get recommendation URL
     *
     * @return string
     */
    public function getRecommendationUrl(): string
    {
        return $this->getUrl('discoverysuite/recommendations/get');
    }

    /**
     * Get tracking URL
     *
     * @return string
     */
    public function getTrackingUrl(): string
    {
        return $this->getUrl('discoverysuite/recommendations/track');
    }

    /**
     * Get widget title
     *
     * @return string
     */
    public function getWidgetTitle(): string
    {
        $context = $this->getContext();
        
        $titles = [
            'homepage' => __('Recommended for You'),
            'product' => __('You May Also Like'),
            'cart' => __('Complete Your Purchase'),
            'category' => __('Popular in This Category'),
            'cross_sell' => __('Frequently Bought Together'),
            'up_sell' => __('Upgrade Your Choice'),
            'similar' => __('Similar Products'),
            'trending' => __('Trending Now')
        ];

        return (string) ($titles[$context] ?? __('Recommended Products'));
    }

    /**
     * Check if should show widget
     *
     * @return bool
     */
    public function shouldShow(): bool
    {
        if (!$this->isEnabled()) {
            return false;
        }

        $context = $this->getContext();
        $configPath = "discovery_suite/recommendations/{$context}_enabled";

        return $this->scopeConfig->isSetFlag(
            $configPath,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Get CSS classes for widget
     *
     * @return string
     */
    public function getCssClasses(): string
    {
        $classes = ['discovery-recommendations-widget'];
        $classes[] = 'context-' . $this->getContext();
        $classes[] = 'layout-' . $this->getLayout();

        return implode(' ', $classes);
    }
}