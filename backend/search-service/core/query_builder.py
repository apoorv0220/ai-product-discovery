"""
Search query builder for Elasticsearch with pagination caps and merchant filter.
"""

from typing import Dict, List, Optional


class SearchQueryBuilder:
    MAX_SIZE = 100
    DEFAULT_SIZE = 20

    def build_product_search_query(
        self,
        merchant_id: int,
        query: str,
        filters: Optional[Dict] = None,
        sort: Optional[str] = None,
        size: int = DEFAULT_SIZE,
        from_: int = 0,
    ) -> Dict:
        size = min(max(1, size), self.MAX_SIZE)
        from_ = max(0, from_)

        must_clauses: List[Dict] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "name^3",
                        "name.autocomplete^2",
                        "categories^2",
                        "description",
                        "short_description",
                        "sku^1.5",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "operator": "or",
                    "minimum_should_match": "70%",
                }
            }
        ]

        filter_clauses: List[Dict] = [{"term": {"merchant_id": merchant_id}}]
        if filters:
            filter_clauses.extend(self._build_filters(filters))

        sort_clause = self._validate_sort(sort)

        return {
            "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
            "sort": sort_clause,
            "size": size,
            "from": from_,
        }

    def _validate_sort(self, sort: Optional[str]) -> List[Dict]:
        valid_sorts = {
            "price_asc": [{"price": "asc"}],
            "price_desc": [{"price": "desc"}],
            "name_asc": [{"name.keyword": "asc"}],
        }
        return valid_sorts.get(sort or "", [{"_score": "desc"}])

    def _build_filters(self, filters: Dict) -> List[Dict]:
        clauses: List[Dict] = []
        if not filters:
            return clauses
        # Price range
        price = filters.get("price")
        if isinstance(price, dict):
            range_q: Dict = {}
            if "min" in price:
                range_q["gte"] = price["min"]
            if "max" in price:
                range_q["lte"] = price["max"]
            if range_q:
                clauses.append({"range": {"price": range_q}})
        # Categories
        categories = filters.get("categories")
        if categories:
            clauses.append({"terms": {"categories.keyword": categories}})
        # Brand
        brand = filters.get("brand")
        if brand:
            clauses.append({"terms": {"brand": brand if isinstance(brand, list) else [brand]}})
        # In-stock
        if filters.get("in_stock") is True:
            clauses.append({"term": {"in_stock": True}})
        return clauses



