<?php
/**
 * DiscoverySuite Update Recommendation Models Cron
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Cron;

use Vendor\DiscoverySuite\Api\RecommendationInterface;
use Vendor\DiscoverySuite\Helper\Data;
use Magento\Sales\Model\ResourceModel\Order\Item\CollectionFactory as OrderItemCollectionFactory;
use Magento\Store\Model\StoreManagerInterface;
use Magento\Framework\Stdlib\DateTime\DateTime;
use Psr\Log\LoggerInterface;

class UpdateRecommendationModels
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
     * @var OrderItemCollectionFactory
     */
    private $orderItemCollectionFactory;

    /**
     * @var StoreManagerInterface
     */
    private $storeManager;

    /**
     * @var DateTime
     */
    private $dateTime;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param RecommendationInterface $recommendationService
     * @param Data $helper
     * @param OrderItemCollectionFactory $orderItemCollectionFactory
     * @param StoreManagerInterface $storeManager
     * @param DateTime $dateTime
     * @param LoggerInterface $logger
     */
    public function __construct(
        RecommendationInterface $recommendationService,
        Data $helper,
        OrderItemCollectionFactory $orderItemCollectionFactory,
        StoreManagerInterface $storeManager,
        DateTime $dateTime,
        LoggerInterface $logger
    ) {
        $this->recommendationService = $recommendationService;
        $this->helper = $helper;
        $this->orderItemCollectionFactory = $orderItemCollectionFactory;
        $this->storeManager = $storeManager;
        $this->dateTime = $dateTime;
        $this->logger = $logger;
    }

    /**
     * Execute recommendation models update
     *
     * @return void
     */
    public function execute(): void
    {
        if (!$this->helper->isRecommendationsEnabled()) {
            return;
        }

        $this->logger->info('Starting recommendation models update');

        try {
            foreach ($this->storeManager->getStores() as $store) {
                $this->updateStoreRecommendationModels((int) $store->getId());
            }

            $this->logger->info('Recommendation models update completed successfully');

        } catch (\Exception $e) {
            $this->logger->error('Recommendation models update failed', [
                'error' => $e->getMessage()
            ]);
        }
    }

    /**
     * Update recommendation models for specific store
     *
     * @param int $storeId
     * @return void
     */
    private function updateStoreRecommendationModels(int $storeId): void
    {
        try {
            // Get recent interaction data for training
            $interactionData = $this->getRecentInteractionData($storeId);
            
            if (!empty($interactionData)) {
                // Send training data to recommendation service
                foreach ($interactionData as $interaction) {
                    $this->recommendationService->trackInteraction(
                        $interaction['user_id'],
                        $interaction['product_id'],
                        $interaction['action'],
                        $interaction['context']
                    );
                }

                $this->logger->info('Recommendation models updated for store', [
                    'store_id' => $storeId,
                    'interactions_processed' => count($interactionData)
                ]);
            }

        } catch (\Exception $e) {
            $this->logger->error('Store recommendation models update failed', [
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);
        }
    }

    /**
     * Get recent interaction data for training
     *
     * @param int $storeId
     * @return array
     */
    private function getRecentInteractionData(int $storeId): array
    {
        $interactions = [];

        try {
            // Get orders from last 4 hours
            $fromDate = $this->dateTime->date('Y-m-d H:i:s', strtotime('-4 hours'));
            
            $orderItemCollection = $this->orderItemCollectionFactory->create();
            $orderItemCollection->getSelect()
                ->join(
                    ['order' => $orderItemCollection->getTable('sales_order')],
                    'main_table.order_id = order.entity_id',
                    ['customer_id', 'created_at', 'store_id']
                )
                ->where('order.store_id = ?', $storeId)
                ->where('order.created_at >= ?', $fromDate);

            foreach ($orderItemCollection as $orderItem) {
                $interactions[] = [
                    'user_id' => $orderItem->getCustomerId() ?: 'guest_' . $orderItem->getOrderId(),
                    'product_id' => $orderItem->getProductId(),
                    'action' => 'purchase',
                    'context' => [
                        'quantity' => $orderItem->getQtyOrdered(),
                        'price' => $orderItem->getPrice(),
                        'timestamp' => $orderItem->getCreatedAt(),
                        'store_id' => $storeId
                    ]
                ];
            }

        } catch (\Exception $e) {
            $this->logger->error('Error getting interaction data', [
                'store_id' => $storeId,
                'error' => $e->getMessage()
            ]);
        }

        return $interactions;
    }
}