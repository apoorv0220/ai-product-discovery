<?php
/**
 * DiscoverySuite Shopping Assistant Widget Block
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Block\Assistant;

use Vendor\DiscoverySuite\Api\AssistantInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Framework\Json\Helper\Data as JsonHelper;
use Magento\Checkout\Model\Session as CheckoutSession;

class Widget extends Template
{
    /**
     * @var AssistantInterface
     */
    private $assistantService;

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
     * @var CheckoutSession
     */
    private $checkoutSession;

    /**
     * Constructor
     *
     * @param Context $context
     * @param AssistantInterface $assistantService
     * @param Data $helper
     * @param CustomerSession $customerSession
     * @param JsonHelper $jsonHelper
     * @param CheckoutSession $checkoutSession
     * @param array $data
     */
    public function __construct(
        Context $context,
        AssistantInterface $assistantService,
        Data $helper,
        CustomerSession $customerSession,
        JsonHelper $jsonHelper,
        CheckoutSession $checkoutSession,
        array $data = []
    ) {
        $this->assistantService = $assistantService;
        $this->helper = $helper;
        $this->customerSession = $customerSession;
        $this->jsonHelper = $jsonHelper;
        $this->checkoutSession = $checkoutSession;
        parent::__construct($context, $data);
    }

    /**
     * Check if shopping assistant is enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->helper->isEnabled();
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
            'sessionEndpoint' => $this->getUrl('discovery/assistant/session'),
            'chatEndpoint' => $this->getUrl('discovery/assistant/chat'),
            'position' => $this->getData('position') ?: 'bottom-right',
            'theme' => $this->getData('theme') ?: 'light',
            'initialContext' => $this->getInitialContext(),
            'welcomeMessage' => $this->getData('welcome_message') ?: __('Hi! How can I help you find the perfect product today?'),
            'placeholderText' => $this->getData('placeholder_text') ?: __('Ask me anything about products...'),
            'minimized' => (bool) $this->getData('minimized')
        ];

        return $this->jsonHelper->jsonEncode($config);
    }

    /**
     * Get user ID for assistant
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
     * Get initial context for the assistant
     *
     * @return array
     */
    private function getInitialContext(): array
    {
        $context = [
            'store_id' => $this->_storeManager->getStore()->getId(),
            'currency' => $this->_storeManager->getStore()->getCurrentCurrency()->getCode(),
            'locale' => $this->_localeResolver->getLocale()
        ];

        // Add cart context if available
        try {
            $quote = $this->checkoutSession->getQuote();
            if ($quote && $quote->getItemsCount() > 0) {
                $context['cart'] = [
                    'item_count' => $quote->getItemsCount(),
                    'subtotal' => $quote->getSubtotal()
                ];
            }
        } catch (\Exception $e) {
            // Ignore cart context if not available
        }

        // Add customer context if logged in
        if ($this->customerSession->isLoggedIn()) {
            $customer = $this->customerSession->getCustomer();
            $context['customer'] = [
                'group_id' => $customer->getGroupId(),
                'is_logged_in' => true
            ];
        }

        return $context;
    }

    /**
     * Get cache key info
     *
     * @return array
     */
    public function getCacheKeyInfo()
    {
        return [
            'DISCOVERY_ASSISTANT',
            $this->_storeManager->getStore()->getId(),
            $this->getUserId(),
            $this->getData('position') ?: 'bottom-right',
            $this->getData('theme') ?: 'light'
        ];
    }
}