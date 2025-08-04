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

use Magento\Framework\View\Element\Template;
use Magento\Framework\View\Element\Template\Context;
use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;
use Magento\Framework\Serialize\Serializer\Json;
use Vendor\DiscoverySuite\Api\AssistantInterface;
use Magento\Customer\Model\Session as CustomerSession;

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
     * @var AssistantInterface
     */
    private $assistantService;

    /**
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * Configuration paths
     */
    const XML_PATH_ASSISTANT_ENABLED = 'discovery_suite/shopping_assistant/enabled';
    const XML_PATH_WIDGET_POSITION = 'discovery_suite/shopping_assistant/widget_position';
    const XML_PATH_CHAT_ENABLED = 'discovery_suite/shopping_assistant/chat_enabled';
    const XML_PATH_GUIDED_FLOW_ENABLED = 'discovery_suite/shopping_assistant/guided_flow_enabled';
    const XML_PATH_AUTO_TRIGGER_DELAY = 'discovery_suite/shopping_assistant/auto_trigger_delay';

    /**
     * @param Context $context
     * @param ScopeConfigInterface $scopeConfig
     * @param Json $jsonSerializer
     * @param AssistantInterface $assistantService
     * @param CustomerSession $customerSession
     * @param array $data
     */
    public function __construct(
        Context $context,
        ScopeConfigInterface $scopeConfig,
        Json $jsonSerializer,
        AssistantInterface $assistantService,
        CustomerSession $customerSession,
        array $data = []
    ) {
        $this->scopeConfig = $scopeConfig;
        $this->jsonSerializer = $jsonSerializer;
        $this->assistantService = $assistantService;
        $this->customerSession = $customerSession;
        parent::__construct($context, $data);
    }

    /**
     * Check if shopping assistant is enabled
     *
     * @return bool
     */
    public function isEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_ASSISTANT_ENABLED,
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
            'position' => $this->getWidgetPosition(),
            'chatEnabled' => $this->isChatEnabled(),
            'guidedFlowEnabled' => $this->isGuidedFlowEnabled(),
            'autoTriggerDelay' => $this->getAutoTriggerDelay(),
            'customerId' => $this->customerSession->getCustomerId(),
            'storeId' => $this->_storeManager->getStore()->getId(),
            'sessionUrl' => $this->getSessionUrl(),
            'chatUrl' => $this->getChatUrl(),
            'flowUrl' => $this->getFlowUrl(),
            'trackingUrl' => $this->getTrackingUrl(),
            'availableFlows' => $this->getAvailableFlows()
        ];

        return $this->jsonSerializer->serialize($config);
    }

    /**
     * Get widget position
     *
     * @return string
     */
    public function getWidgetPosition(): string
    {
        return $this->scopeConfig->getValue(
            self::XML_PATH_WIDGET_POSITION,
            ScopeInterface::SCOPE_STORE
        ) ?: 'bottom_right';
    }

    /**
     * Check if chat is enabled
     *
     * @return bool
     */
    public function isChatEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_CHAT_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Check if guided flow is enabled
     *
     * @return bool
     */
    public function isGuidedFlowEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag(
            self::XML_PATH_GUIDED_FLOW_ENABLED,
            ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Get auto trigger delay
     *
     * @return int
     */
    public function getAutoTriggerDelay(): int
    {
        return (int) $this->scopeConfig->getValue(
            self::XML_PATH_AUTO_TRIGGER_DELAY,
            ScopeInterface::SCOPE_STORE
        ) ?: 30;
    }

    /**
     * Get available flows
     *
     * @return array
     */
    public function getAvailableFlows(): array
    {
        try {
            return $this->assistantService->getAvailableFlows();
        } catch (\Exception $e) {
            $this->_logger->error('Failed to get available flows', [
                'error' => $e->getMessage()
            ]);
            return [];
        }
    }

    /**
     * Get session URL
     *
     * @return string
     */
    public function getSessionUrl(): string
    {
        return $this->getUrl('discoverysuite/assistant/session');
    }

    /**
     * Get chat URL
     *
     * @return string
     */
    public function getChatUrl(): string
    {
        return $this->getUrl('discoverysuite/assistant/chat');
    }

    /**
     * Get flow URL
     *
     * @return string
     */
    public function getFlowUrl(): string
    {
        return $this->getUrl('discoverysuite/assistant/flow');
    }

    /**
     * Get tracking URL
     *
     * @return string
     */
    public function getTrackingUrl(): string
    {
        return $this->getUrl('discoverysuite/assistant/track');
    }

    /**
     * Get CSS classes for widget position
     *
     * @return string
     */
    public function getPositionClasses(): string
    {
        $position = $this->getWidgetPosition();
        $classes = ['discovery-assistant-widget'];
        
        switch ($position) {
            case 'bottom_left':
                $classes[] = 'position-bottom-left';
                break;
            case 'bottom_right':
                $classes[] = 'position-bottom-right';
                break;
            case 'top_left':
                $classes[] = 'position-top-left';
                break;
            case 'top_right':
                $classes[] = 'position-top-right';
                break;
            case 'center':
                $classes[] = 'position-center';
                break;
            default:
                $classes[] = 'position-bottom-right';
        }

        return implode(' ', $classes);
    }

    /**
     * Check if should show widget
     *
     * @return bool
     */
    public function shouldShow(): bool
    {
        return $this->isEnabled();
    }

    /**
     * Get welcome message
     *
     * @return string
     */
    public function getWelcomeMessage(): string
    {
        return __('Hi! I\'m your AI shopping assistant. How can I help you find the perfect product today?');
    }
}