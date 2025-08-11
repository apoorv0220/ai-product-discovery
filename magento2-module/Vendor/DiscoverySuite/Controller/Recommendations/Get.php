<?php
/**
 * DiscoverySuite Get Recommendations Controller
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
use Magento\Framework\App\Action\HttpGetActionInterface;
use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Magento\Customer\Model\Session as CustomerSession;
use Psr\Log\LoggerInterface;

class Get implements HttpGetActionInterface, HttpPostActionInterface
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
     * Execute get recommendations action
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->resultJsonFactory->create();

        if (!$this->helper->isRecommendationsEnabled()) {
            return $result->setData([
                'success' => false,
                'message' => 'Recommendations are disabled',
                'recommendations' => []
            ]);
        }

        try {
            $context = (string) $this->request->getParam('context', 'homepage');
            $limit = (int) $this->request->getParam('limit', 12);
            $productId = $this->request->getParam('product_id');
            
            $userId = $this->getUserId();

            if ($productId) {
                // Get similar products
                $recommendations = $this->recommendationService->getSimilarProducts(
                    (int) $productId,
                    $limit
                );
            } else {
                // Get personalized recommendations
                $filters = $this->getFiltersFromRequest();
                $recommendations = $this->recommendationService->getRecommendations(
                    $userId,
                    $context,
                    $limit,
                    $filters
                );
            }

            return $result->setData([
                'success' => true,
                'context' => $context,
                'user_id' => $userId,
                'recommendations' => $recommendations
            ]);

        } catch (\Exception $e) {
            $this->logger->error('Get recommendations request failed', [
                'context' => $this->request->getParam('context', ''),
                'user_id' => $this->getUserId(),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'success' => false,
                'message' => 'Recommendations request failed',
                'recommendations' => []
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

    /**
     * Get filters from request
     *
     * @return array
     */
    private function getFiltersFromRequest(): array
    {
        $filters = [];

        if ($categoryId = $this->request->getParam('category_id')) {
            $filters['category_id'] = (int) $categoryId;
        }

        if ($priceRange = $this->request->getParam('price_range')) {
            $filters['price_range'] = $priceRange;
        }

        if ($brands = $this->request->getParam('brands')) {
            $filters['brands'] = is_array($brands) ? $brands : explode(',', $brands);
        }

        return $filters;
    }
}