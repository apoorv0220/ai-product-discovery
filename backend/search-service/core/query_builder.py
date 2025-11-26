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
        aggregations: Optional[Dict] = None,
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

        query_dict = {
            "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
            "sort": sort_clause,
            "size": size,
            "from": from_,
        }
        
        # Add aggregations if provided
        if aggregations:
            query_dict["aggs"] = aggregations
        
        return query_dict

    def _validate_sort(self, sort: Optional[str]) -> List[Dict]:
        valid_sorts = {
            "price_asc": [{"price": "asc"}],
            "price_desc": [{"price": "desc"}],
            "name_asc": [{"name.keyword": "asc"}],
        }
        return valid_sorts.get(sort or "", [{"_score": "desc"}])

    def _build_filters(self, filters: Dict) -> List[Dict]:
        """
        Build filter clauses from filter dictionary.
        
        Multi-select logic: OR within facet, AND between facets
        - categories: ["Shoes", "Bags"] -> OR (products in Shoes OR Bags)
        - brands: ["Nike"] AND categories: ["Shoes", "Bags"] -> AND (Nike AND (Shoes OR Bags))
        """
        clauses: List[Dict] = []
        if not filters:
            return clauses
        
        # Price range filter
        price = filters.get("price")
        if isinstance(price, dict):
            range_q: Dict = {}
            if "min" in price:
                range_q["gte"] = price["min"]
            if "max" in price:
                range_q["lte"] = price["max"]
            if range_q:
                clauses.append({"range": {"price": range_q}})
        
        # Categories filter (multi-select: OR within facet)
        categories = filters.get("categories")
        if categories:
            # Ensure it's a list
            if not isinstance(categories, list):
                categories = [categories]
            if categories:
                clauses.append({"terms": {"categories.keyword": categories}})
        
        # Brands filter (multi-select: OR within facet)
        brands = filters.get("brands") or filters.get("brand")
        if brands:
            # Ensure it's a list
            if not isinstance(brands, list):
                brands = [brands]
            if brands:
                clauses.append({"terms": {"brand.keyword": brands}})
        
        # Rating filter (range)
        rating = filters.get("rating")
        if isinstance(rating, dict):
            range_q: Dict = {}
            if "min" in rating:
                range_q["gte"] = rating["min"]
            if "max" in rating:
                range_q["lte"] = rating["max"]
            if range_q:
                clauses.append({"range": {"avg_rating": range_q}})
        
        # In-stock filter (boolean)
        in_stock = filters.get("in_stock")
        if in_stock is not None:
            clauses.append({"term": {"in_stock": bool(in_stock)}})
        
        # Status filter
        status = filters.get("status")
        if status is not None:
            clauses.append({"term": {"status": status}})
        
        return clauses



