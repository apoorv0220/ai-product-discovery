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

use Vendor\DiscoverySuite\Model\Search\SearchService;
use Vendor\DiscoverySuite\Helper\Data;
use Vendor\DiscoverySuite\Model\Api\HttpClient;
use PHPUnit\Framework\TestCase;
use PHPUnit\Framework\MockObject\MockObject;
use Psr\Log\LoggerInterface;

class SearchServiceTest extends TestCase
{
    /**
     * @var SearchService
     */
    private $searchService;

    /**
     * @var Data|MockObject
     */
    private $helperMock;

    /**
     * @var HttpClient|MockObject
     */
    private $httpClientMock;

    /**
     * @var LoggerInterface|MockObject
     */
    private $loggerMock;

    /**
     * Set up test
     */
    protected function setUp(): void
    {
        $this->helperMock = $this->createMock(Data::class);
        $this->httpClientMock = $this->createMock(HttpClient::class);
        $this->loggerMock = $this->createMock(LoggerInterface::class);

        $this->searchService = new SearchService(
            $this->helperMock,
            $this->httpClientMock,
            $this->loggerMock
        );
    }

    /**
     * Test search method when service is disabled
     */
    public function testSearchWhenDisabled()
    {
        $this->helperMock->expects($this->once())
            ->method('isSearchEnabled')
            ->willReturn(false);

        $result = $this->searchService->search('test query');

        $this->assertEmpty($result);
    }

    /**
     * Test search method when service is enabled
     */
    public function testSearchWhenEnabled()
    {
        $expectedResponse = [
            'products' => [
                ['id' => 1, 'name' => 'Test Product 1'],
                ['id' => 2, 'name' => 'Test Product 2']
            ],
            'total' => 2
        ];

        $this->helperMock->expects($this->once())
            ->method('isSearchEnabled')
            ->willReturn(true);

        $this->helperMock->expects($this->once())
            ->method('getServiceUrl')
            ->with('search', '/api/v1/search/')
            ->willReturn('http://localhost:7001/api/v1/search/');

        $this->httpClientMock->expects($this->once())
            ->method('post')
            ->with(
                'http://localhost:7001/api/v1/search/',
                [
                    'query' => 'test query',
                    'limit' => 20,
                    'offset' => 0,
                    'filters' => []
                ]
            )
            ->willReturn($expectedResponse);

        $result = $this->searchService->search('test query');

        $this->assertEquals($expectedResponse, $result);
    }

    /**
     * Test autocomplete method when service is disabled
     */
    public function testAutocompleteWhenDisabled()
    {
        $this->helperMock->expects($this->once())
            ->method('isAutocompleteEnabled')
            ->willReturn(false);

        $result = $this->searchService->autocomplete('test');

        $this->assertEmpty($result);
    }

    /**
     * Test autocomplete method when service is enabled
     */
    public function testAutocompleteWhenEnabled()
    {
        $expectedResponse = [
            'suggestions' => [
                'test product 1',
                'test product 2',
                'test category'
            ]
        ];

        $this->helperMock->expects($this->once())
            ->method('isAutocompleteEnabled')
            ->willReturn(true);

        $this->helperMock->expects($this->once())
            ->method('getServiceUrl')
            ->with('search', '/api/v1/autocomplete/')
            ->willReturn('http://localhost:7001/api/v1/autocomplete/');

        $this->httpClientMock->expects($this->once())
            ->method('post')
            ->with(
                'http://localhost:7001/api/v1/autocomplete/',
                [
                    'query' => 'test',
                    'limit' => 10
                ]
            )
            ->willReturn($expectedResponse);

        $result = $this->searchService->autocomplete('test');

        $this->assertEquals($expectedResponse['suggestions'], $result);
    }

    /**
     * Test indexProducts method
     */
    public function testIndexProducts()
    {
        $products = [
            ['id' => 1, 'name' => 'Product 1'],
            ['id' => 2, 'name' => 'Product 2']
        ];

        $this->helperMock->expects($this->once())
            ->method('isEnabled')
            ->willReturn(true);

        $this->helperMock->expects($this->once())
            ->method('getServiceUrl')
            ->with('search', '/api/v1/index/')
            ->willReturn('http://localhost:7001/api/v1/index/');

        $this->httpClientMock->expects($this->once())
            ->method('post')
            ->with(
                'http://localhost:7001/api/v1/index/',
                ['products' => $products]
            )
            ->willReturn(['success' => true]);

        $result = $this->searchService->indexProducts($products);

        $this->assertTrue($result);
    }

    /**
     * Test deleteProduct method
     */
    public function testDeleteProduct()
    {
        $productId = 123;

        $this->helperMock->expects($this->once())
            ->method('isEnabled')
            ->willReturn(true);

        $this->helperMock->expects($this->once())
            ->method('getServiceUrl')
            ->with('search', '/api/v1/index/123')
            ->willReturn('http://localhost:7001/api/v1/index/123');

        $this->httpClientMock->expects($this->once())
            ->method('delete')
            ->with('http://localhost:7001/api/v1/index/123')
            ->willReturn(['success' => true]);

        $result = $this->searchService->deleteProduct($productId);

        $this->assertTrue($result);
    }
}