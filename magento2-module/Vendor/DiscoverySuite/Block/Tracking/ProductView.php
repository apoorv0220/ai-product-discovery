<?php
/**
 * Product View Tracking Block
 * Provides product data for personalized search tracking
 */

namespace Vendor\DiscoverySuite\Block\Tracking;

use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Framework\Registry;
use Magento\Catalog\Model\Product;
use Magento\Customer\Model\Session as CustomerSession;
use Psr\Log\LoggerInterface;

class ProductView extends Template
{
    /**
     * @var Registry
     */
    protected $registry;

    /**
     * @var CustomerSession
     */
    protected $customerSession;

    /**
     * @var LoggerInterface
     */
    protected $logger;

    /**
     * Constructor
     *
     * @param Context $context
     * @param Registry $registry
     * @param CustomerSession $customerSession
     * @param LoggerInterface $logger
     * @param array $data
     */
    public function __construct(
        Context $context,
        Registry $registry,
        CustomerSession $customerSession,
        LoggerInterface $logger,
        array $data = []
    ) {
        $this->registry = $registry;
        $this->customerSession = $customerSession;
        $this->logger = $logger;
        parent::__construct($context, $data);
    }

    /**
     * Get current product
     *
     * @return Product|null
     */
    public function getCurrentProduct(): ?Product
    {
        return $this->registry->registry('current_product');
    }

    /**
     * Get product data for tracking
     *
     * @return array
     */
    public function getProductData(): array
    {
        $product = $this->getCurrentProduct();
        
        if (!$product) {
            return [];
        }

        try {
            $categories = [];
            foreach ($product->getCategoryCollection() as $category) {
                $categories[] = $category->getName();
            }

            return [
                'id' => $product->getId(),
                'name' => $product->getName(),
                'sku' => $product->getSku(),
                'categories' => $categories,
                'price' => $product->getPrice(),
                'url' => $product->getProductUrl()
            ];
        } catch (\Exception $e) {
            $this->logger->error('Error getting product data for tracking', [
                'error' => $e->getMessage(),
                'product_id' => $product->getId()
            ]);
            return [];
        }
    }

    /**
     * Get user ID
     *
     * @return string|null
     */
    public function getUserId(): ?string
    {
        if ($this->customerSession->isLoggedIn()) {
            return (string) $this->customerSession->getCustomerId();
        }
        return null;
    }

    /**
     * Get tracking API URL
     *
     * @return string
     */
    public function getTrackingUrl(): string
    {
        return $this->getUrl('discovery/tracking/productview');
    }

    /**
     * Check if user came from search
     *
     * @return bool
     */
    public function isCameFromSearch(): bool
    {
        $referer = $this->getRequest()->getServer('HTTP_REFERER', '');
        return strpos($referer, '/catalogsearch/result/') !== false || 
               $this->getRequest()->getParam('q') !== null;
    }

    /**
     * Get search query if came from search
     *
     * @return string
     */
    public function getSearchQuery(): string
    {
        return (string) $this->getRequest()->getParam('q', '');
    }

    /**
     * Get product data as JSON
     *
     * @return string
     */
    public function getProductDataJson(): string
    {
        return json_encode($this->getProductData());
    }
}
