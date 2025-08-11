<?php
/**
 * DiscoverySuite Analytics Pixel Block
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Block\Analytics;

use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Framework\Json\Helper\Data as JsonHelper;
use Magento\Framework\Registry;
use Magento\Checkout\Model\Session as CheckoutSession;

class Pixel extends Template
{
    /**
     * @var Data
     */
    private $helper;

    /**
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * @var JsonHelper
     */
    private $jsonHelper;

    /**
     * @var Registry
     */
    private $registry;

    /**
     * @var CheckoutSession
     */
    private $checkoutSession;

    /**
     * Constructor
     *
     * @param Context $context
     * @param Data $helper
     * @param CustomerSession $customerSession
     * @param JsonHelper $jsonHelper
     * @param Registry $registry
     * @param CheckoutSession $checkoutSession
     * @param array $data
     */
    public function __construct(
        Context $context,
        Data $helper,
        CustomerSession $customerSession,
        JsonHelper $jsonHelper,
        Registry $registry,
        CheckoutSession $checkoutSession,
        array $data = []
    ) {
        $this->helper = $helper;
        $this->customerSession = $customerSession;
        $this->jsonHelper = $jsonHelper;
        $this->registry = $registry;
        $this->checkoutSession = $checkoutSession;
        parent::__construct($context, $data);
    }

    /**
     * Check if analytics tracking is enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->helper->isAnalyticsEnabled();
    }

    /**
     * Get analytics configuration as JSON
     *
     * @return string
     */
    public function getConfigJson(): string
    {
        if (!$this->isEnabled()) {
            return '{}';
        }

        $config = [
            'enabled' => true,
            'userId' => $this->getUserId(),
            'trackingEndpoint' => $this->getUrl('discovery/analytics/track'),
            'pageData' => $this->getPageData(),
            'sessionData' => $this->getSessionData(),
            'autoTrack' => [
                'pageView' => true,
                'productView' => true,
                'categoryView' => true,
                'searchQuery' => true,
                'addToCart' => true,
                'removeFromCart' => true,
                'checkout' => true,
                'purchase' => true
            ]
        ];

        return $this->jsonHelper->jsonEncode($config);
    }

    /**
     * Get user ID for analytics
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
     * Get current page data
     *
     * @return array
     */
    private function getPageData(): array
    {
        $pageData = [
            'type' => $this->getPageType(),
            'url' => $this->getRequest()->getUriString(),
            'referrer' => $this->getRequest()->getServer('HTTP_REFERER'),
            'title' => $this->pageConfig->getTitle()->get()
        ];

        // Add product-specific data
        $currentProduct = $this->registry->registry('current_product');
        if ($currentProduct) {
            $pageData['product'] = [
                'id' => $currentProduct->getId(),
                'sku' => $currentProduct->getSku(),
                'name' => $currentProduct->getName(),
                'price' => $currentProduct->getPrice(),
                'category_ids' => $currentProduct->getCategoryIds()
            ];
        }

        // Add category-specific data
        $currentCategory = $this->registry->registry('current_category');
        if ($currentCategory) {
            $pageData['category'] = [
                'id' => $currentCategory->getId(),
                'name' => $currentCategory->getName(),
                'path' => $currentCategory->getPath()
            ];
        }

        return $pageData;
    }

    /**
     * Get session data
     *
     * @return array
     */
    private function getSessionData(): array
    {
        $sessionData = [
            'store_id' => $this->_storeManager->getStore()->getId(),
            'currency' => $this->_storeManager->getStore()->getCurrentCurrency()->getCode(),
            'locale' => $this->_localeResolver->getLocale(),
            'is_logged_in' => $this->customerSession->isLoggedIn()
        ];

        // Add cart data if available
        try {
            $quote = $this->checkoutSession->getQuote();
            if ($quote && $quote->getItemsCount() > 0) {
                $sessionData['cart'] = [
                    'item_count' => $quote->getItemsCount(),
                    'subtotal' => $quote->getSubtotal(),
                    'items' => []
                ];

                foreach ($quote->getAllVisibleItems() as $item) {
                    $sessionData['cart']['items'][] = [
                        'product_id' => $item->getProductId(),
                        'sku' => $item->getSku(),
                        'name' => $item->getName(),
                        'qty' => $item->getQty(),
                        'price' => $item->getPrice()
                    ];
                }
            }
        } catch (\Exception $e) {
            // Ignore cart data if not available
        }

        return $sessionData;
    }

    /**
     * Determine page type
     *
     * @return string
     */
    private function getPageType(): string
    {
        $fullActionName = $this->getRequest()->getFullActionName();

        switch ($fullActionName) {
            case 'cms_index_index':
                return 'homepage';
            case 'catalog_product_view':
                return 'product';
            case 'catalog_category_view':
                return 'category';
            case 'catalogsearch_result_index':
                return 'search';
            case 'checkout_cart_index':
                return 'cart';
            case 'checkout_index_index':
            case 'checkout_onepage_index':
                return 'checkout';
            case 'checkout_onepage_success':
                return 'purchase_success';
            default:
                return 'other';
        }
    }
}