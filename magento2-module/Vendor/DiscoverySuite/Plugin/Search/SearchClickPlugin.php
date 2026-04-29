<?php
/**
 * DiscoverySuite Search Click Plugin
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Plugin\Search;

use Magento\Framework\App\RequestInterface;
use Magento\Framework\App\Response\RedirectInterface;
use Magento\Framework\Session\SessionManagerInterface;
use Magento\Customer\Model\Session as CustomerSession;

class SearchClickPlugin
{
    protected $request;
    protected $redirect;
    protected $customerSession;
;


    public function __construct(
        RequestInterface $request,
        RedirectInterface $redirect,
        CustomerSession $customerSession
    ) {
        $this->request = $request;
        $this->redirect = $redirect;
        $this->customerSession = $customerSession;
    }

    public function beforeExecute()
    {
        try{
        $referer = $this->redirect->getRefererUrl();

        if (!$referer || strpos($referer, 'catalogsearch/result') === false) {
            return;
        }

        $query = parse_url($referer, PHP_URL_QUERY);
        parse_str($query, $params);

        if (empty($params['q'])) {
            return;
        }

        /** Session handling */
        if ($this->customerSession->isLoggedIn()) {
            $customerId = $this->customerSession->getCustomerId();
               
                $sessionId = 'customer_' . $customerId;
            } else {
                $sessionId = 'guest_' . $this->sessionManager->getSessionId();
            }
        $productId = (string)$this->request->getParam('id');

        $payload = [
            'session_id'   => $sessionId,
            'search_query' => $params['q'],
            'clicked_product_id'   => $productId,
            'platform'     => 'magento'
        ];

               try {
                /** API CALL */
            $response = $this->apiClient->post(
                '/api/v1/tracking/bulk-ingest',
                $payload
            
            );
            } catch (Exception $e) {
             $e->getMessage();
            }
            
            /** LOG RESPONSE (this is your "print") */
            $this->logger->info(
                'DiscoverySuite Search Click Response',
                $response
            );
        } catch(Exception $e){
               $this->logger->error('DiscoverySuite Search Click Failed');
        }

    }
}