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

use Magento\Framework\Event\Observer;
use Magento\Framework\Event\ObserverInterface;
use Magento\Framework\App\RequestInterface;
use Magento\Framework\Session\SessionManagerInterface;
use Magento\Customer\Model\Session as CustomerSession;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Psr\Log\LoggerInterface;
use Magento\Catalog\Model\Layer\Resolver as LayerResolver;
use Vendor\DiscoverySuite\Model\BulkDataCollector;

class SearchQueriesObserver implements ObserverInterface
{
    protected $request;
    protected $sessionManager;
    protected $customerSession;
    protected $apiClient;
    protected $logger;

    protected $layerResolver;
    protected $bulkDataCollector;
    public function __construct(
        RequestInterface $request,
        SessionManagerInterface $sessionManager,
        CustomerSession $customerSession,
        HttpClient $apiClient,
        LoggerInterface $logger,
        LayerResolver $layerResolver,
        BulkDataCollector $bulkDataCollector
    ) {
        $this->request = $request;
        $this->sessionManager = $sessionManager;
        $this->customerSession = $customerSession;
        $this->apiClient = $apiClient;
        $this->logger = $logger;
        $this->layerResolver = $layerResolver;
        $this->bulkDataCollector = $bulkDataCollector;
    }

    public function execute(Observer $observer)
    {
        try {
            /** Search query */
            $query = trim((string) $this->request->getParam('q'));
            if (empty($query)) {
                return;
            }

            /** Session ID */
            if ($this->customerSession->isLoggedIn()) {
                $sessionId = 'customer_' . $this->customerSession->getCustomerId();
            } else {
                $sessionId = 'guest_' . $this->sessionManager->getSessionId();
            }

            /** Search results (product IDs + names) */
            $results = [];
            // $collection = $observer->getEvent()->getResultCollection();

            $layer = $this->layerResolver->get();
            $collection = $layer->getProductCollection();

            /** Load search result products */
            // $collection = $this->collectionFactory->create();
            // $collection->addSearchFilter($query);
            // $collection->addAttributeToSelect(['name', 'price']);
            // $collection->setPageSize(20);

            $products = [];
            $position = 1;

            foreach ($collection as $product) {
                $products[] = [
                    'product_id'   => (string)$product->getId(),
                    'sku'          => $product->getSku(),
                    'product_name' => $product->getName(),
                    'price'        => (float)$product->getFinalPrice(),
                    'position'     => $position++
                ];
            }
            /** Payload */
            $this->bulkDataCollector->addSearchQuery([
                    'session_id' => $sessionId,
                    'query'      => $query,
                    'results'    => $products,
                    'platform'   => 'magento'
            ]);
        } catch (\Exception $e) {
            $this->logger->error(
                'DiscoverySuite Search Query Error: ' . $e->getMessage()
            );
        }
    }
}
