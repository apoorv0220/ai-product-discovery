"""
AI Product Discovery Suite - Elasticsearch Configuration

@category    Backend
@package     Shared
@author      AI Product Discovery Team
@copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
@license     https://opensource.org/licenses/MIT MIT License
"""

from typing import Dict, Any
from shared.config.settings import get_settings

settings = get_settings()


# Elasticsearch index mappings
PRODUCT_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "product_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "asciifolding",
                        "stop",
                        "synonym_filter",
                        "stemmer"
                    ]
                },
                "autocomplete_analyzer": {
                    "type": "custom",
                    "tokenizer": "keyword",
                    "filter": [
                        "lowercase",
                        "asciifolding",
                        "autocomplete_filter"
                    ]
                }
            },
            "filter": {
                "synonym_filter": {
                    "type": "synonym",
                    "synonyms_path": "synonyms/synonyms.txt"
                },
                "autocomplete_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20
                }
            }
        }
    },
    "mappings": {
        "properties": {
            # Basic product info
            "id": {"type": "integer"},
            "magento_product_id": {"type": "integer"},
            "store_id": {"type": "integer"},
            "sku": {
                "type": "text",
                "analyzer": "keyword",
                "fields": {
                    "suggest": {
                        "type": "text",
                        "analyzer": "autocomplete_analyzer"
                    }
                }
            },
            "name": {
                "type": "text",
                "analyzer": "product_analyzer",
                "fields": {
                    "suggest": {
                        "type": "text",
                        "analyzer": "autocomplete_analyzer"
                    },
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "description": {
                "type": "text",
                "analyzer": "product_analyzer"
            },
            "short_description": {
                "type": "text",
                "analyzer": "product_analyzer"
            },
            
            # Pricing
            "price": {"type": "float"},
            "special_price": {"type": "float"},
            "cost": {"type": "float"},
            
            # Status and visibility
            "status": {"type": "integer"},
            "visibility": {"type": "integer"},
            "is_in_stock": {"type": "boolean"},
            "qty": {"type": "float"},
            
            # Categories
            "category_ids": {"type": "integer"},
            "primary_category_id": {"type": "integer"},
            "category_names": {
                "type": "text",
                "analyzer": "product_analyzer",
                "fields": {
                    "suggest": {
                        "type": "text",
                        "analyzer": "autocomplete_analyzer"
                    }
                }
            },
            
            # Attributes (dynamic)
            "attributes": {
                "type": "object",
                "dynamic": True
            },
            
            # SEO
            "url_key": {"type": "keyword"},
            "meta_title": {"type": "text"},
            "meta_description": {"type": "text"},
            
            # Images
            "image_url": {"type": "keyword"},
            "thumbnail_url": {"type": "keyword"},
            
            # AI/ML fields
            "embedding_vector": {
                "type": "dense_vector",
                "dims": 768
            },
            "ai_tags": {
                "type": "text",
                "analyzer": "product_analyzer"
            },
            "quality_score": {"type": "float"},
            "sentiment_score": {"type": "float"},
            
            # Analytics
            "view_count": {"type": "integer"},
            "purchase_count": {"type": "integer"},
            "conversion_rate": {"type": "float"},
            "popularity_score": {"type": "float"},
            "avg_rating": {"type": "float"},
            "review_count": {"type": "integer"},
            
            # Boost and ranking
            "boost_score": {"type": "float"},
            "manual_boost": {"type": "float"},
            "search_boost": {"type": "float"},
            
            # Timestamps
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "last_synced_at": {"type": "date"}
        }
    }
}


SEARCH_LOG_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index.lifecycle.name": "search_logs_policy",
        "index.lifecycle.rollover_alias": "search_logs"
    },
    "mappings": {
        "properties": {
            "query_id": {"type": "keyword"},
            "query_text": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "normalized_query": {"type": "keyword"},
            "store_id": {"type": "integer"},
            "user_id": {"type": "integer"},
            "session_id": {"type": "keyword"},
            "ip_address": {"type": "ip"},
            "user_agent": {"type": "text"},
            "search_type": {"type": "keyword"},
            "total_results": {"type": "integer"},
            "results_shown": {"type": "integer"},
            "clicked_results": {"type": "integer"},
            "search_time_ms": {"type": "integer"},
            "fallback_used": {"type": "boolean"},
            "filters_applied": {"type": "object"},
            "created_at": {"type": "date"},
            "@timestamp": {"type": "date"}
        }
    }
}


ANALYTICS_EVENT_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "index.lifecycle.name": "analytics_policy",
        "index.lifecycle.rollover_alias": "analytics_events"
    },
    "mappings": {
        "properties": {
            "event_id": {"type": "keyword"},
            "event_type": {"type": "keyword"},
            "event_data": {"type": "object", "dynamic": True},
            "user_id": {"type": "integer"},
            "session_id": {"type": "keyword"},
            "visitor_id": {"type": "keyword"},
            "store_id": {"type": "integer"},
            "ip_address": {"type": "ip"},
            "user_agent": {"type": "text"},
            "referrer": {"type": "keyword"},
            "page_url": {"type": "keyword"},
            "country": {"type": "keyword"},
            "region": {"type": "keyword"},
            "city": {"type": "keyword"},
            "device_type": {"type": "keyword"},
            "browser": {"type": "keyword"},
            "os": {"type": "keyword"},
            "load_time_ms": {"type": "integer"},
            "ab_test_id": {"type": "keyword"},
            "ab_test_variant": {"type": "keyword"},
            "created_at": {"type": "date"},
            "@timestamp": {"type": "date"}
        }
    }
}


# Index lifecycle policies
SEARCH_LOGS_ILM_POLICY = {
    "policy": {
        "phases": {
            "hot": {
                "actions": {
                    "rollover": {
                        "max_size": "50gb",
                        "max_age": "30d"
                    }
                }
            },
            "warm": {
                "min_age": "30d",
                "actions": {
                    "shrink": {
                        "number_of_shards": 1
                    },
                    "forcemerge": {
                        "max_num_segments": 1
                    }
                }
            },
            "cold": {
                "min_age": "90d",
                "actions": {
                    "allocate": {
                        "number_of_replicas": 0
                    }
                }
            },
            "delete": {
                "min_age": "365d"
            }
        }
    }
}


ANALYTICS_ILM_POLICY = {
    "policy": {
        "phases": {
            "hot": {
                "actions": {
                    "rollover": {
                        "max_size": "100gb",
                        "max_age": "7d"
                    }
                }
            },
            "warm": {
                "min_age": "7d",
                "actions": {
                    "shrink": {
                        "number_of_shards": 1
                    },
                    "forcemerge": {
                        "max_num_segments": 1
                    }
                }
            },
            "cold": {
                "min_age": "30d",
                "actions": {
                    "allocate": {
                        "number_of_replicas": 0
                    }
                }
            },
            "delete": {
                "min_age": "90d"
            }
        }
    }
}


def get_index_name(base_name: str, store_id: int = None) -> str:
    """Get index name with optional store prefix"""
    prefix = settings.ELASTICSEARCH_INDEX_PREFIX
    if store_id:
        return f"{prefix}_{base_name}_store_{store_id}"
    return f"{prefix}_{base_name}"


def get_product_index_name(store_id: int) -> str:
    """Get product index name for specific store"""
    return get_index_name("products", store_id)


def get_search_logs_index_name() -> str:
    """Get search logs index name"""
    return get_index_name("search_logs")


def get_analytics_index_name() -> str:
    """Get analytics events index name"""
    return get_index_name("analytics_events")


# Search templates
PRODUCT_SEARCH_TEMPLATE = {
    "script": {
        "lang": "mustache",
        "source": {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": "{{query}}",
                                "fields": [
                                    "name^3",
                                    "name.suggest^2",
                                    "description^1",
                                    "sku^2",
                                    "ai_tags^1.5",
                                    "category_names^1.5"
                                ],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"store_id": "{{store_id}}"}},
                        {"term": {"status": 1}},
                        {"terms": {"visibility": [2, 3, 4]}}
                    ]
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"popularity_score": {"order": "desc"}},
                {"avg_rating": {"order": "desc"}}
            ],
            "_source": [
                "id", "magento_product_id", "sku", "name", 
                "price", "special_price", "image_url", 
                "url_key", "avg_rating", "review_count"
            ],
            "from": "{{from}}",
            "size": "{{size}}"
        }
    }
}


AUTOCOMPLETE_TEMPLATE = {
    "script": {
        "lang": "mustache",
        "source": {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": "{{query}}",
                                "fields": [
                                    "name.suggest^3",
                                    "sku.suggest^2",
                                    "category_names.suggest^1"
                                ],
                                "type": "phrase_prefix"
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"store_id": "{{store_id}}"}},
                        {"term": {"status": 1}},
                        {"terms": {"visibility": [2, 3, 4]}}
                    ]
                }
            },
            "aggs": {
                "suggestions": {
                    "terms": {
                        "field": "name.keyword",
                        "size": "{{size}}"
                    }
                },
                "categories": {
                    "terms": {
                        "field": "category_names.keyword",
                        "size": 5
                    }
                }
            },
            "_source": ["id", "name", "image_url", "price"],
            "size": "{{size}}"
        }
    }
}