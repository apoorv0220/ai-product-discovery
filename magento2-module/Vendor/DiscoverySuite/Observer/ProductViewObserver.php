<?php
/**
 * DiscoverySuite Search Query Observer
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Observer;

use Exception;
use Magento\Framework\Event\Observer;
use Magento\Framework\Event\ObserverInterface;
use Magento\Customer\Model\Session as CustomerSession;
use Magento\Framework\Session\SessionManagerInterface;
use Magento\Catalog\Api\CategoryRepositoryInterface;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Psr\Log\LoggerInterface;
use Vendor\DiscoverySuite\Model\BulkDataCollector;

class ProductViewObserver implements ObserverInterface
{
    protected  $customerSession;
    protected  $sessionManager;
    protected  $categoryRepository;
    protected  $apiClient;
    protected $logger;
    protected $bulkDataCollector;

    public function __construct(
        CustomerSession $customerSession,
        SessionManagerInterface $sessionManager,
        CategoryRepositoryInterface $categoryRepository,
        HttpClient $apiClient,
        LoggerInterface $logger,
        BulkDataCollector $bulkDataCollector
    ) {
        $this->customerSession = $customerSession;
        $this->sessionManager = $sessionManager;
        $this->categoryRepository = $categoryRepository;
        $this->apiClient = $apiClient;
        $this->logger = $logger;
        $this->bulkDataCollector = $bulkDataCollector;
    }

    public function execute(Observer $observer)
    {
        try {
            /** @var \Magento\Catalog\Model\Product $product */
            $product = $observer->getEvent()->getProduct();
            if (!$product || !$product->getId()) {
                return;
            }

            /** Session handling */
            if ($this->customerSession->isLoggedIn()) {
                $customerId = $this->customerSession->getCustomerId();
               
                $sessionId = 'customer_' . $customerId;
            } else {
                $sessionId = 'guest_' . $this->sessionManager->getSessionId();
            }

            /** Category names */
            $categoryNames = [];
            foreach ($product->getCategoryIds() as $categoryId) {
                try {
                    $category = $this->categoryRepository->get($categoryId);
                    $categoryNames[] = $category->getName();
                } catch (\Exception $e) {
                    continue;
                }
            }

            /** Payload */
            $this->bulkDataCollector->addProductView([
                    'session_id'    => $sessionId,
                    'product_id'    => (string) $product->getId(),
                    'product_name'  => (string) $product->getName(),
                    'categories'    => $categoryNames,
                    'view_duration' => 30,
                    'platform'      => 'magento'
            ]);

        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite Product View Error: ' . $e->getMessage()
            );
        }
    }
}