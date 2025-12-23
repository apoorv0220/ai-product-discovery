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
        merchandising_rules: Optional[List] = None,
    ) -> Dict:
        import structlog
        logger = structlog.get_logger()
        size = min(max(1, size), self.MAX_SIZE)
        from_ = max(0, from_)

        must_clauses: List[Dict] = [
            {
                "function_score": {
                    "query": {
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
                    },
                    "functions": [
                        {
                            "filter": {"exists": {"field": "brand"}},
                            "weight": 1.2  # Boost products with brand info
                        },
                        {
                            "filter": {"exists": {"field": "attributes.color"}},
                            "weight": 1.1  # Boost products with color attributes
                        },
                        {
                            "filter": {"exists": {"field": "attributes.material"}},
                            "weight": 1.1  # Boost products with material info
                        },
                        {
                            "filter": {"term": {"categories": "hoodies & sweatshirts"}},
                            "weight": 1.3  # Generic category boost (works for all domains)
                        },
                        {
                            "filter": {"term": {"categories": "tees"}},
                            "weight": 1.3  # Generic category boost (works for all domains)
                        }
                    ],
                    "score_mode": "multiply",
                    "boost_mode": "multiply"
                }
            }
        ]

        # Add merchandising boost rules if provided
        if merchandising_rules:
            # Extract boost rules
            boost_rules = [r for r in merchandising_rules if r.get("rule_type") == "boost"]
            if boost_rules:
                # Apply boosts to the function_score query
                function_score = must_clauses[0].get("function_score", {})
                functions = function_score.get("functions", [])

                for rule in boost_rules:
                    boost_factor = rule.get("action_config", {}).get("boost_factor", 1.0)
                    boost_factor = min(10.0, max(0.1, float(boost_factor)))

                    # Use target_conditions if present, otherwise fall back to old conditions
                    target_conditions = rule.get("target_conditions") or rule.get("conditions")
                    logger.info(f"Processing boost rule: target_conditions={target_conditions}")
                    if target_conditions:
                        filter_clause = self._build_merchandising_filter(target_conditions)
                        logger.info(f"Built filter clause: {filter_clause}")
                        if filter_clause:
                            functions.append({
                                "filter": filter_clause,
                                "weight": boost_factor
                            })
                
                # Update functions list
                if functions:
                    must_clauses[0]["function_score"]["functions"] = functions
                    # Use sum for additive boosts (merchandising + existing)
                    must_clauses[0]["function_score"]["score_mode"] = "sum"
                    logger.info(f"Added {len(functions)} boost functions to query")

        filter_clauses = self._build_filters(filters)
        sort_clause = self._validate_sort(sort)

        query_dict = {
            "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
            "sort": sort_clause,
            "size": size,
            "from": from_,
        }

        try:
            # Add aggregations if provided
            if aggregations:
                query_dict["aggs"] = aggregations

            return query_dict
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error(f"Query builder failed at final stage: {e}", exc_info=True)
            return None

    def _build_merchandising_filter(self, conditions: Dict) -> Optional[Dict]:
        """
        Build Elasticsearch filter from merchandising rule conditions

        Args:
            conditions: Condition dictionary from rule

        Returns:
            Elasticsearch filter clause or None
        """
        import structlog
        logger = structlog.get_logger()
        logger.info(f"_build_merchandising_filter called with conditions: {conditions}")
        condition_type = conditions.get("type")
        operator = conditions.get("operator")
        value = conditions.get("value")
        logger.info(f"condition_type={condition_type}, operator={operator}, value={value}")
        
        if condition_type == "product_id":
            if operator == "equals":
                return {"term": {"product_id": str(value)}}
            elif operator == "in":
                if isinstance(value, list):
                    return {"terms": {"product_id": [str(v) for v in value]}}
                else:
                    return {"term": {"product_id": str(value)}}
        
        elif condition_type == "category":
            if operator == "equals":
                return {"term": {"categories.keyword": str(value)}}
            elif operator == "in":
                if isinstance(value, list):
                    return {"terms": {"categories.keyword": [str(v) for v in value]}}
                else:
                    return {"term": {"categories.keyword": str(value)}}
        
        # For query_match, we can't create a static filter (depends on query)
        # This is handled in the search API by evaluating rules before building query
        return None

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

        try:
            # Add aggregations if provided
            if aggregations:
                query_dict["aggs"] = aggregations

            # Log merchandising function count
            functions_count = 0
            if merchandising_rules:
                boost_rules = [r for r in merchandising_rules if r.get("rule_type") == "boost"]
                if boost_rules:
                    fs = must_clauses[0].get("function_score", {})
                    functions_count = len(fs.get("functions", []))
            logger.info(f"Query built with {functions_count} merchandising boost functions")

            return query_dict
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error(f"Query builder failed: {e}", exc_info=True)
            return None

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



