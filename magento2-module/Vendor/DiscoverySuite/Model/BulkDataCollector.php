<?php
namespace Vendor\DiscoverySuite\Model;

class BulkDataCollector
{
    private $productViews = [];
    private $searchQueries = [];
    private $searchClicks = [];

    public function addProductView(array $data)
    {
        $this->productViews[] = $data;
    }

    public function addSearchQuery(array $data)
    {
        $this->searchQueries[] = $data;
    }

    public function addSearchClick(array $data)
    {
        $this->searchClicks[] = $data;
    }

    public function getPayload(): array
    {
        return array_filter([
            'product_views'  => $this->productViews,
            'search_queries' => $this->searchQueries,
            'search_clicks'  => $this->searchClicks
        ]);
    }

    public function isEmpty(): bool
    {
        return empty($this->productViews)
            && empty($this->searchQueries)
            && empty($this->searchClicks);
    }
}
