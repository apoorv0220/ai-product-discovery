<?php
/**
 * DiscoverySuite Recommendations Get Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Controller\Recommendations;

use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Controller\ResultInterface;
use Vendor\DiscoverySuite\Api\RecommendationInterface;
use Psr\Log\LoggerInterface;

class Get implements HttpPostActionInterface
{
    /**
     * @var RequestInterface
     */
    private $request;

    /**
     * @var JsonFactory
     */
    private $jsonFactory;

    /**
     * @var RecommendationInterface
     */
    private $recommendationService;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * @param RequestInterface $request
     * @param JsonFactory $jsonFactory
     * @param RecommendationInterface $recommendationService
     * @param LoggerInterface $logger
     */
    public function __construct(
        RequestInterface $request,
        JsonFactory $jsonFactory,
        RecommendationInterface $recommendationService,
        LoggerInterface $logger
    ) {
        $this->request = $request;
        $this->jsonFactory = $jsonFactory;
        $this->recommendationService = $recommendationService;
        $this->logger = $logger;
    }

    /**
     * Execute recommendations request
     *
     * @return ResultInterface
     */
    public function execute(): ResultInterface
    {
        $result = $this->jsonFactory->create();

        try {
            $context = $this->request->getParam('context', 'homepage');
            $storeId = (int) $this->request->getParam('store_id');
            $customerId = $this->request->getParam('customer_id') ? (int) $this->request->getParam('customer_id') : null;
            $limit = (int) $this->request->getParam('limit', 12);
            $productId = $this->request->getParam('product_id') ? (int) $this->request->getParam('product_id') : null;

            // Build parameters based on context
            $params = [];
            if ($productId) {
                $params['product_id'] = $productId;
            }

            // Get recommendations
            $recommendations = $this->recommendationService->getRecommendations(
                $context,
                $params,
                $customerId,
                $storeId,
                $limit
            );

            // Format response
            $response = [
                'success' => true,
                'products' => $this->formatProducts($recommendations['products'] ?? []),
                'total_count' => $recommendations['total_count'] ?? 0,
                'recommendation_id' => $recommendations['recommendation_id'] ?? null,
                'context' => $context,
                'has_more' => ($recommendations['total_count'] ?? 0) > $limit
            ];

            return $result->setData($response);

        } catch (\Exception $e) {
            $this->logger->error('Recommendations controller error', [
                'context' => $this->request->getParam('context'),
                'error' => $e->getMessage()
            ]);

            return $result->setData([
                'success' => false,
                'error' => 'Unable to load recommendations',
                'products' => []
            ]);
        }
    }

    /**
     * Format products for frontend display
     *
     * @param array $products
     * @return array
     */
    private function formatProducts(array $products): array
    {
        $formatted = [];

        foreach ($products as $product) {
            $formatted[] = [
                'id' => $product['id'] ?? 0,
                'name' => $product['name'] ?? '',
                'url' => $this->getProductUrl($product),
                'image' => $product['image_url'] ?? null,
                'price' => $product['price'] ?? 0,
                'special_price' => $product['special_price'] ?? null,
                'formatted_price' => $this->formatPrice($product['price'] ?? 0),
                'formatted_special_price' => $this->formatPrice($product['special_price'] ?? null),
                'rating' => $product['avg_rating'] ?? 0,
                'review_count' => $product['review_count'] ?? 0,
                'is_saleable' => $product['is_in_stock'] ?? true,
                'sku' => $product['sku'] ?? ''
            ];
        }

        return $formatted;
    }

    /**
     * Get product URL
     *
     * @param array $product
     * @return string
     */
    private function getProductUrl(array $product): string
    {
        // This would typically use Magento's URL builder
        $urlKey = $product['url_key'] ?? '';
        return $urlKey ? "/{$urlKey}.html" : "#";
    }

    /**
     * Format price for display
     *
     * @param float|null $price
     * @return string|null
     */
    private function formatPrice(?float $price): ?string
    {
        if ($price === null) {
            return null;
        }

        return '$' . number_format($price, 2);
    }
}