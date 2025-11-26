"""
Elasticsearch index settings and mappings for product search.
"""

from typing import Dict, List


def get_product_index_settings(synonyms: List[str]) -> Dict:
    return {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "product_name_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "product_synonym"],
                },
                "autocomplete_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "autocomplete_filter"],
                },
                "autocomplete_search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
            },
            "filter": {
                "autocomplete_filter": {"type": "edge_ngram", "min_gram": 2, "max_gram": 20},
                "product_synonym": {"type": "synonym", "synonyms": synonyms or []},
            },
        },
    }


PRODUCT_INDEX_MAPPING: Dict = {
    "properties": {
        "merchant_id": {"type": "integer"},
        "product_id": {"type": "keyword"},
        "sku": {"type": "keyword"},
        "name": {
            "type": "text",
            "analyzer": "product_name_analyzer",
            "fields": {
                "keyword": {"type": "keyword"},
                "autocomplete": {
                    "type": "text",
                    "analyzer": "autocomplete_analyzer",
                    "search_analyzer": "autocomplete_search_analyzer",
                },
            },
        },
        "description": {"type": "text", "analyzer": "product_name_analyzer"},
        "short_description": {"type": "text"},
        "price": {"type": "float"},
        "special_price": {"type": "float"},
        "final_price": {"type": "float"},
        "currency": {"type": "keyword"},
        "categories": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "category_ids": {"type": "keyword"},
        "brand": {"type": "keyword"},
        "status": {"type": "integer"},
        "visibility": {"type": "integer"},
        "in_stock": {"type": "boolean"},
        "stock_quantity": {"type": "integer"},
        "manage_stock": {"type": "boolean"},
        "store_id": {"type": "integer"},
        "website_id": {"type": "integer"},
        "avg_rating": {"type": "float"},
        "review_count": {"type": "integer"},
        "attributes": {"type": "object", "enabled": False},
        # Flattened attributes for faceting
        "attr_color": {"type": "keyword"},
        "attr_size": {"type": "keyword"},
        "attr_material": {"type": "keyword"},
        "attr_pattern": {"type": "keyword"},
        "attr_climate": {"type": "keyword"},
        "url": {"type": "keyword"},
        "image_url": {"type": "keyword"},
        "created_at": {"type": "date"},
        "updated_at": {"type": "date"},
    }
}



