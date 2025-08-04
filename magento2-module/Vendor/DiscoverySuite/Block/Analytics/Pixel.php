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

use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;
use Magento\Framework\Serialize\Serializer\Json;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Framework\Registry;

class Pixel extends Template
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
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * @var Registry
     */
    private $registry;

    /**
     * Configuration paths
     */
    const XML_PATH_ANALYTICS_ENABLED = 'discovery_suite/analytics/enabled';
    const XML_PATH_TRACK_SEARCHES = 'discovery_suite/analytics/track_searches';
    const XML_PATH_TRACK_CLICKS = 'discovery_suite/analytics/track_clicks';
    const XML_PATH_TRACK_PURCHASES = 'discovery_suite/analytics/track_purchases';
    const XML_PATH_TRACK_PAGE_VIEWS = 'discovery_suite/analytics/track_page_views';
    const XML_PATH_AB_TESTING_ENABLED = 'discovery_suite/analytics/ab_testing_enabled';

    /**
     * @param Context $context
     * @param ScopeConfigInterface $scopeConfig
     * @param Json $jsonSerializer
     * @param CustomerSession $customerSession
     * @param Registry $registry
     * @param array $data
     */
    public function __construct(
        Context $context,
        ScopeConfigInterface $scopeConfig,
        Json $jsonSerializer,
        CustomerSession $customerSession,
        Registry $registry,
        array $data = []
    ) {
        $this->scopeConfig = $scopeConfig;
        $this->jsonSerializer = $jsonSerializer;
        $this->customerSession = $customerSession;
        $this->registry = $registry;
        parent::__construct($context, $data);
    }

    /**
     * Check if analytics is enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_ANALYTICS_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Get analytics configuration
     *
     * @return string JSON encoded configuration
     */
    public function getAnalyticsConfig(): string
    {
        $config = [
            'enabled' => $this->isEnabled(),
            'trackSearches' => $this->isTrackSearchesEnabled(),
            'trackClicks' => $this->isTrackClicksEnabled(),
            'trackPurchases' => $this->isTrackPurchasesEnabled(),
            'trackPageViews' => $this->isTrackPageViewsEnabled(),
            'abTestingEnabled' => $this->isABTestingEnabled(),
            'customerId' => $this->customerSession->getCustomerId(),
            'storeId' => $this->_storeManager->getStore()->getId(),
            'sessionId' => $this->_session->getSessionId(),
            'trackingUrl' => $this->getTrackingUrl(),
            'pageData' => $this->getPageData()
        ];

        return $this->jsonSerializer->serialize($config);
    }

    /**
     * Check if search tracking is enabled
     *
     * @return bool
     */
    public function isTrackSearchesEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_TRACK_SEARCHES,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if click tracking is enabled
     *
     * @return bool
     */
    public function isTrackClicksEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_TRACK_CLICKS,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if purchase tracking is enabled
     *
     * @return bool
     */
    public function isTrackPurchasesEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_TRACK_PURCHASES,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if page view tracking is enabled
     *
     * @return bool
     */
    public function isTrackPageViewsEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_TRACK_PAGE_VIEWS,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if A/B testing is enabled
     *
     * @return bool
     */
    public function isABTestingEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_AB_TESTING_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Get tracking URL
     *
     * @return string
     */
    public function getTrackingUrl(): string
    {
        return $this->getUrl('discoverysuite/analytics/track');
    }

    /**
     * Get current page data
     *
     * @return array
     */
    public function getPageData(): array
    {
        $request = $this->getRequest();
        $fullActionName = $request->getFullActionName();
        
        $pageData = [
            'page_type' => $this->getPageType($fullActionName),
            'page_url' => $request->getUriString(),
            'page_title' => $this->getPageTitle(),
            'full_action_name' => $fullActionName,
            'route_name' => $request->getRouteName(),
            'controller_name' => $request->getControllerName(),
            'action_name' => $request->getActionName()
        ];

        // Add context-specific data
        switch ($pageData['page_type']) {
            case 'product':
                $product = $this->registry->registry('current_product');
                if ($product) {
                    $pageData['product_id'] = $product->getId();
                    $pageData['product_sku'] = $product->getSku();
                    $pageData['product_name'] = $product->getName();
                    $pageData['product_price'] = $product->getPrice();
                    $pageData['category_ids'] = $product->getCategoryIds();
                }
                break;
                
            case 'category':
                $category = $this->registry->registry('current_category');
                if ($category) {
                    $pageData['category_id'] = $category->getId();
                    $pageData['category_name'] = $category->getName();
                    $pageData['category_path'] = $category->getPath();
                }
                break;
                
            case 'search':
                $pageData['search_query'] = $request->getParam('q', '');
                break;
        }

        return $pageData;
    }

    /**
     * Get page type from full action name
     *
     * @param string $fullActionName
     * @return string
     */
    private function getPageType(string $fullActionName): string
    {
        $pageTypeMap = [
            'cms_index_index' => 'homepage',
            'catalog_product_view' => 'product',
            'catalog_category_view' => 'category',
            'catalogsearch_result_index' => 'search',
            'checkout_cart_index' => 'cart',
            'checkout_index_index' => 'checkout',
            'checkout_onepage_success' => 'success',
            'customer_account_index' => 'account',
            'customer_account_login' => 'login',
            'customer_account_create' => 'register'
        ];

        return $pageTypeMap[$fullActionName] ?? 'other';
    }

    /**
     * Get page title
     *
     * @return string
     */
    private function getPageTitle(): string
    {
        return $this->pageConfig->getTitle()->get() ?: '';
    }

    /**
     * Get A/B test variants for current page
     *
     * @return array
     */
    public function getABTestVariants(): array
    {
        // This would typically fetch active A/B tests from the service
        // For now, return empty array
        return [];
    }
}