<?php
/**
 * DiscoverySuite Assistant Chat Controller
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

namespace Vendor\DiscoverySuite\Controller\Assistant;

use Magento\Framework\App\Action\HttpPostActionInterface;
use Magento\Framework\Controller\Result\JsonFactory;
use Magento\Framework\Session\SessionManagerInterface;
use Magento\Framework\App\RequestInterface;
use Vendor\DiscoverySuite\Model\Assistant\AssistantService;
use Psr\Log\LoggerInterface;

class Chat implements HttpPostActionInterface
{
    /**
     * @var JsonFactory
     */
    private $jsonFactory;

    /**
     * @var SessionManagerInterface
     */
    private $sessionManager;

    /**
     * @var RequestInterface
     */
    private $request;

    /**
     * @var AssistantService
     */
    private $assistantService;

    /**
     * @var LoggerInterface
     */
    private $logger;

    /**
     * Constructor
     *
     * @param JsonFactory $jsonFactory
     * @param SessionManagerInterface $sessionManager
     * @param RequestInterface $request
     * @param AssistantService $assistantService
     * @param LoggerInterface $logger
     */
    public function __construct(
        JsonFactory $jsonFactory,
        SessionManagerInterface $sessionManager,
        RequestInterface $request,
        AssistantService $assistantService,
        LoggerInterface $logger
    ) {
        $this->jsonFactory = $jsonFactory;
        $this->sessionManager = $sessionManager;
        $this->request = $request;
        $this->assistantService = $assistantService;
        $this->logger = $logger;
    }

    /**
     * Handle chat message
     *
     * @return \Magento\Framework\Controller\Result\Json
     */
    public function execute()
    {
        try {
            $message = $this->request->getParam('message');
            $sessionId = $this->sessionManager->getSessionId();
            $userId = $this->request->getParam('user_id');
            $contextData = $this->request->getParam('context_data', []);
            
            if (empty($message)) {
                return $this->jsonFactory->create()->setData([
                    'error' => 'Message is required',
                    'status' => 'error'
                ])->setHttpResponseCode(400);
            }
            
            // Send message to assistant service
            $response = $this->assistantService->chat($message, $sessionId, $userId, $contextData);
            
            $this->logger->info('Assistant chat processed', [
                'session_id' => $sessionId,
                'user_id' => $userId,
                'message_length' => strlen($message)
            ]);
            
            return $this->jsonFactory->create()->setData($response);
            
        } catch (\Exception $e) {
            $this->logger->error('Assistant chat error', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            return $this->jsonFactory->create()->setData([
                'error' => 'Failed to process chat message',
                'status' => 'error'
            ])->setHttpResponseCode(500);
        }
    }
}
