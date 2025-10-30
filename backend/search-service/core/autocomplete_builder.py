"""
Autocomplete query builder using edge n-gram and match_phrase_prefix.
"""

from typing import Dict


class AutocompleteQueryBuilder:
    def build_autocomplete_query(self, merchant_id: int, query: str, limit: int = 10) -> Dict:
        return {
            "query": {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "should": [
                                    {"match": {"name.autocomplete": {"query": query, "boost": 3}}},
                                    {"match_phrase_prefix": {"name": {"query": query, "boost": 2}}},
                                    {"wildcard": {"name.keyword": {"value": f"*{query}*", "boost": 0.5}}},
                                ]
                            }
                        }
                    ],
                    "filter": [{"term": {"merchant_id": merchant_id}}],
                }
            },
            "_source": ["product_id", "name", "price", "currency", "image_url"],
            "size": min(limit, 20),
        }



