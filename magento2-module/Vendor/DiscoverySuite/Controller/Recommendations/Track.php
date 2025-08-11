<?php
/**
 * DiscoverySuite Track Recommendation Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Controller\Recommendations;

use Vendor\DiscoverySuite\Api\RecommendationInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Magento\Customer\Model\Session as CustomerSession;
use Psr\Log\LoggerInterface;

class Track implements HttpPostActionInterface
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
     * @var RequestInterface
     */
    private $request;

    /**
     * @var JsonFactory
     */
    private $resultJsonFactory;

    /**
     * @var CustomerSession
     */
    private $customerSession;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param RecommendationInterface $recommendationService
     * @param Data $helper
     * @param RequestInterface $request
     * @param JsonFactory $resultJsonFactory
     * @param CustomerSession $customerSession
     * @param LoggerInterface $logger
     */
    public function __construct(
        RecommendationInterface $recommendationService,
        Data $helper,
        RequestInterface $request,
        JsonFactory $resultJsonFactory,
        CustomerSession $customerSession,
        LoggerInterface $logger
    ) {
        $this->recommendationService = $recommendationService;
        $this->helper = $helper;
        $this->request = $request;
        $this->resultJsonFactory = $resultJsonFactory;
        $this->customerSession = $customerSession;
        $this->logger = $logger;
    }

    /**
     * Execute track interaction action
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->resultJsonFactory->create();

        if (!$this->helper->isRecommendationsEnabled()) {
            return $result->setData([
                'success' => false,
                'message' => 'Recommendations tracking is disabled'
            ]);
        }

        try {
            $productId = (int) $this->request->getParam('product_id');
            $action = (string) $this->request->getParam('action');
            $context = $this->request->getParam('context', []);

            if (!$productId || !$action) {
                return $result->setData([
                    'success' => false,
                    'message' => 'Missing required parameters'
                ]);
            }

            $userId = $this->getUserId();

            // Add additional context
            if (!is_array($context)) {
                $context = [];
            }
            
            $context['timestamp'] = time();
            $context['source'] = 'recommendation_widget';

            $tracked = $this->recommendationService->trackInteraction(
                $userId,
                $productId,
                $action,
                $context
            );

            if ($tracked) {
                return $result->setData([
                    'success' => true,
                    'message' => 'Interaction tracked successfully'
                ]);
            } else {
                return $result->setData([
                    'success' => false,
                    'message' => 'Failed to track interaction'
                ]);
            }

        } catch (\Exception $e) {
            $this->logger->error('Track recommendation interaction failed', [
                'product_id' => $this->request->getParam('product_id'),
                'action' => $this->request->getParam('action'),
                'user_id' => $this->getUserId(),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'success' => false,
                'message' => 'Tracking request failed'
            ]);
        }
    }

    /**
     * Get user ID
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
}