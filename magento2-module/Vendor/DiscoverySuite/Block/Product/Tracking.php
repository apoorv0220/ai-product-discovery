<?php
/**
 * Product Tracking Block for Personalized Search
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Block\Product;

use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Framework\Session\SessionManagerInterface;
use Vendor\DiscoverySuite\Helper\Data;

class Tracking extends Template
{
    /**
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * @var SessionManagerInterface
     */
    private $sessionManager;

    /**
     * @var Data
     */
    private $helper;

    /**
     * @param Context $context
     * @param CustomerSession $customerSession
     * @param SessionManagerInterface $sessionManager
     * @param Data $helper
     * @param array $data
     */
    public function __construct(
        Context $context,
        CustomerSession $customerSession,
        SessionManagerInterface $sessionManager,
        Data $helper,
        array $data = []
    ) {
        $this->customerSession = $customerSession;
        $this->sessionManager = $sessionManager;
        $this->helper = $helper;
        parent::__construct($context, $data);
    }

    /**
     * Get current user ID
     *
     * @return string
     */
    public function getUserId(): string
    {
        if ($this->customerSession->isLoggedIn()) {
            return 'customer_' . $this->customerSession->getCustomerId();
        }
        
        return 'guest_' . $this->sessionManager->getSessionId();
    }

    /**
     * Get session ID
     *
     * @string
     */
    public function getSessionId(): string
    {
        return $this->sessionManager->getSessionId();
    }

    /**
     * Get API endpoint for tracking
     *
     * @return string
     */
    public function getTrackingEndpoint(): string
    {
        return $this->helper->getServiceUrl('search', '/api/v1/interactions/');
    }

    /**
     * Get search endpoint
     *
     * @return string
     */
    public function getSearchEndpoint(): string
    {
        return $this->helper->getSearchEndpoint();
    }

    /**
     * Check if tracking is enabled
     *
     * @return bool
     */
    public function isTrackingEnabled(): bool
    {
        return $this->helper->isEnabled() && $this->helper->isSearchEnabled();
    }

    /**
     * Get current product data for tracking
     *
     * @return array
     */
    public function getCurrentProductData(): array
    {
        $product = $this->getData('product');
        
        if (!$product) {
            return [];
        }

        return [
            'id' => $product->getId(),
            'sku' => $product->getSku(),
            'name' => $product->getName(),
            'categories' => $this->getProductCategories($product),
            'price' => $product->getPrice(),
            'url' => $product->getProductUrl()
        ];
    }

    /**
     * Get product categories
     *
     * @param \Magento\Catalog\Model\Product $product
     * @return array
     */
    private function getProductCategories($product): array
    {
        $categoryIds = $product->getCategoryIds();
        $categories = [];
        
        if ($categoryIds) {
            $categoryCollection = $this->getCategoryCollection();
            foreach ($categoryIds as $categoryId) {
                $category = $categoryCollection->getItemById($categoryId);
                if ($category) {
                    $categories[] = $category->getName();
                }
            }
        }
        
        return $categories;
    }

    /**
     * Get category collection
     *
     * @return \Magento\Catalog\Model\ResourceModel\Category\Collection
     */
    private function getCategoryCollection()
    {
        $objectManager = \Magento\Framework\App\ObjectManager::getInstance();
        return $objectManager->create(\Magento\Catalog\Model\ResourceModel\Category\Collection::class);
    }

    /**
     * Get tracking configuration as JSON
     *
     * @return string
     */
    public function getTrackingConfigJson(): string
    {
        $config = [
            'api_endpoint' => $this->getTrackingEndpoint(),
            'search_endpoint' => $this->getSearchEndpoint(),
            'user_id' => $this->getUserId(),
            'session_id' => $this->getSessionId(),
            'enabled' => $this->isTrackingEnabled()
        ];

        return json_encode($config);
    }
}
