<?php
/**
 * DiscoverySuite Search Service Unit Test
 *
 * @category    Vendor
 * @package     Vendor_DiscoverySuite
 * @author      AI Product Discovery Team
 * @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
 * @license     https://opensource.org/licenses/MIT MIT License
 */

declare(strict_types=1);

namespace Vendor\DiscoverySuite\Test\Unit\Model\Search;

use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;
use Vendor\DiscoverySuite\Model\Search\SearchService;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use Vendor\DiscoverySuite\Helper\Config;
use Magento\Store\Model\StoreManagerInterface;
use Magento\Customer\Model\Session as CustomerSession;
use Psr\Log\LoggerInterface;

class SearchServiceTest extends TestCase
{
    /**
     * @var SearchService
     */
    private $searchService;

    /**
     * @var HttpClient|MockObject
     */
    private $httpClientMock;

    /**
     * @var Config|MockObject
     */
    private $configHelperMock;

    /**
     * @var StoreManagerInterface|MockObject
     */
    private $storeManagerMock;

    /**
     * @var CustomerSession|MockObject
     */
    private $customerSessionMock;

    /**
     * @var LoggerInterface|MockObject
     */
    private $loggerMock;

    /**
     * Set up test fixtures
     */
    protected function setUp(): void
    {
        $this->httpClientMock = $this->createMock(HttpClient::class);
        $this->configHelperMock = $this->createMock(Config::class);
        $this->storeManagerMock = $this->createMock(StoreManagerInterface::class);
        $this->customerSessionMock = $this->createMock(CustomerSession::class);
        $this->loggerMock = $this->createMock(LoggerInterface::class);

        $this->searchService = new SearchService(
            $this->httpClientMock,
            $this->configHelperMock,
            $this->storeManagerMock,
            $this->customerSessionMock,
            $this->loggerMock
        );
    }

    /**
     * Test search functionality
     */
    public function testSearch(): void
    {
        $searchQuery = 'test product';
        $storeId = 1;
        $expectedResponse = [
            'products' => [
                ['id' => 1, 'name' => 'Test Product 1'],
                ['id' => 2, 'name' => 'Test Product 2']
            ],
            'total_count' => 2,
            'took' => 50
        ];

        $this->configHelperMock->expects($this->once())
            ->method('isEnabled')
            ->willReturn(true);

        $this->httpClientMock->expects($this->once())
            ->method('post')
            ->with('/search', $this->isType('array'))
            ->willReturn($expectedResponse);

        $result = $this->searchService->search($searchQuery, [], null, $storeId);

        $this->assertEquals($expectedResponse, $result);
    }

    /**
     * Test search with disabled module
     */
    public function testSearchWithDisabledModule(): void
    {
        $this->configHelperMock->expects($this->once())
            ->method('isEnabled')
            ->willReturn(false);

        $this->httpClientMock->expects($this->never())
            ->method('post');

        $result = $this->searchService->search('test', [], null, 1);

        $this->assertEquals(['products' => [], 'total_count' => 0], $result);
    }

    /**
     * Test autocomplete functionality
     */
    public function testAutocomplete(): void
    {
        $query = 'test';
        $expectedResponse = [
            'suggestions' => ['test product', 'test item'],
            'products' => [
                ['id' => 1, 'name' => 'Test Product']
            ]
        ];

        $this->configHelperMock->expects($this->once())
            ->method('isEnabled')
            ->willReturn(true);

        $this->httpClientMock->expects($this->once())
            ->method('post')
            ->with('/autocomplete', $this->isType('array'))
            ->willReturn($expectedResponse);

        $result = $this->searchService->autocomplete($query, [], null, 1);

        $this->assertEquals($expectedResponse, $result);
    }

    /**
     * Test sync product functionality
     */
    public function testSyncProduct(): void
    {
        $productData = [
            'id' => 1,
            'name' => 'Test Product',
            'price' => 99.99
        ];

        $this->configHelperMock->expects($this->once())
            ->method('isEnabled')
            ->willReturn(true);

        $this->httpClientMock->expects($this->once())
            ->method('post')
            ->with('/sync/product', $productData)
            ->willReturn(['success' => true]);

        $result = $this->searchService->syncProduct($productData, 1);

        $this->assertTrue($result);
    }

    /**
     * Test error handling
     */
    public function testSearchWithError(): void
    {
        $this->configHelperMock->expects($this->once())
            ->method('isEnabled')
            ->willReturn(true);

        $this->httpClientMock->expects($this->once())
            ->method('post')
            ->willThrowException(new \Exception('API Error'));

        $this->loggerMock->expects($this->once())
            ->method('error');

        $result = $this->searchService->search('test', [], null, 1);

        $this->assertEquals(['products' => [], 'total_count' => 0], $result);
    }
}