"""
AI Product Discovery Suite - Facet Generation

Generates dynamic facets for search results using Elasticsearch aggregations.

@category    Backend
@package     SearchService/Core
@license     MIT License
"""

from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class FacetValue:
    """Represents a single facet value"""
    def __init__(self, value: str, count: int, selected: bool = False):
        self.value = value
        self.count = count
        self.selected = selected
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "value": self.value,
            "count": self.count,
            "selected": self.selected
        }


class Facet:
    """Represents a facet with multiple values"""
    def __init__(self, name: str, values: List[FacetValue], facet_type: str = "terms"):
        self.name = name
        self.values = values
        self.facet_type = facet_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "type": self.facet_type,
            "values": [v.to_dict() for v in self.values]
        }


class FacetGenerator:
    """
    Generates facets from Elasticsearch aggregation results.
    
    Supports:
    - Category facets (hierarchical)
    - Brand facets
    - Price range facets
    - Attribute facets (dynamic)
    - Rating facets
    - Availability facets
    """
    
    # Facet types
    FACET_TYPES = {
        "category": "terms",
        "brand": "terms",
        "price": "range",
        "rating": "range",
        "availability": "terms",
        "attributes": "terms"
    }
    
    # Price range buckets
    PRICE_RANGES = [
        {"from": 0, "to": 50, "label": "$0 - $50"},
        {"from": 50, "to": 100, "label": "$50 - $100"},
        {"from": 100, "to": 200, "label": "$100 - $200"},
        {"from": 200, "to": 500, "label": "$200 - $500"},
        {"from": 500, "label": "$500+"}
    ]
    
    # Rating range buckets
    RATING_RANGES = [
        {"from": 4.0, "label": "4+ Stars"},
        {"from": 3.0, "to": 4.0, "label": "3-4 Stars"},
        {"from": 2.0, "to": 3.0, "label": "2-3 Stars"},
        {"from": 0, "to": 2.0, "label": "Below 2 Stars"}
    ]
    
    def build_aggregations(self, facet_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Build Elasticsearch aggregations for facet extraction
        
        Args:
            facet_types: List of facet types to include (None = all)
            
        Returns:
            Aggregations dictionary
        """
        facet_types = facet_types or list(self.FACET_TYPES.keys())
        aggs = {}
        
        if "category" in facet_types:
            aggs["categories"] = {
                "terms": {
                    "field": "categories.keyword",
                    "size": 20,
                    "order": {"_count": "desc"}
                }
            }
        
        if "brand" in facet_types:
            aggs["brands"] = {
                "terms": {
                    "field": "brand.keyword",
                    "size": 20,
                    "order": {"_count": "desc"}
                }
            }
        
        if "price" in facet_types:
            aggs["price_ranges"] = {
                "range": {
                    "field": "price",
                    "ranges": [
                        {"from": r["from"], "to": r.get("to"), "key": r["label"]}
                        for r in self.PRICE_RANGES
                    ]
                }
            }
        
        if "rating" in facet_types:
            aggs["ratings"] = {
                "range": {
                    "field": "avg_rating",
                    "ranges": [
                        {"from": r["from"], "to": r.get("to"), "key": r["label"]}
                        for r in self.RATING_RANGES
                    ]
                }
            }
        
        if "availability" in facet_types:
            aggs["availability"] = {
                "terms": {
                    "field": "in_stock",
                    "size": 2
                }
            }
        
        # Add attribute facets
        if "attributes" in facet_types:
            # Color facet
            aggs["attr_color"] = {
                "terms": {
                    "field": "attr_color",
                    "size": 20,
                    "order": {"_count": "desc"}
                }
            }
            # Size facet
            aggs["attr_size"] = {
                "terms": {
                    "field": "attr_size",
                    "size": 20,
                    "order": {"_count": "desc"}
                }
            }
            # Material facet
            aggs["attr_material"] = {
                "terms": {
                    "field": "attr_material",
                    "size": 20,
                    "order": {"_count": "desc"}
                }
            }
            # Pattern facet
            aggs["attr_pattern"] = {
                "terms": {
                    "field": "attr_pattern",
                    "size": 20,
                    "order": {"_count": "desc"}
                }
            }
            # Climate facet
            aggs["attr_climate"] = {
                "terms": {
                    "field": "attr_climate",
                    "size": 20,
                    "order": {"_count": "desc"}
                }
            }
        
        return aggs
    
    def parse_aggregations(
        self,
        aggregations: Dict[str, Any],
        selected_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Facet]:
        """
        Parse Elasticsearch aggregation results into Facet objects
        
        Args:
            aggregations: Aggregation results from Elasticsearch
            selected_filters: Currently selected filter values
            
        Returns:
            Dictionary of facet name to Facet object
        """
        facets = {}
        selected_filters = selected_filters or {}
        
        # Parse category facets
        if "categories" in aggregations:
            buckets = aggregations["categories"].get("buckets", [])
            values = []
            selected_categories = selected_filters.get("categories", [])
            if not isinstance(selected_categories, list):
                selected_categories = [selected_categories] if selected_categories else []
            
            for bucket in buckets:
                value = bucket["key"]
                count = bucket["doc_count"]
                selected = value in selected_categories
                values.append(FacetValue(value, count, selected))
            
            if values:
                facets["categories"] = Facet("categories", values, "terms")
        
        # Parse brand facets
        if "brands" in aggregations:
            buckets = aggregations["brands"].get("buckets", [])
            values = []
            selected_brands = selected_filters.get("brands", [])
            if not isinstance(selected_brands, list):
                selected_brands = [selected_brands] if selected_brands else []
            
            for bucket in buckets:
                value = bucket["key"]
                count = bucket["doc_count"]
                selected = value in selected_brands
                values.append(FacetValue(value, count, selected))
            
            if values:
                facets["brands"] = Facet("brands", values, "terms")
        
        # Parse price range facets
        if "price_ranges" in aggregations:
            buckets = aggregations["price_ranges"].get("buckets", [])
            values = []
            selected_price = selected_filters.get("price", {})
            
            for bucket in buckets:
                value = bucket["key"]
                count = bucket["doc_count"]
                # Check if this range is selected
                selected = False
                if isinstance(selected_price, dict):
                    range_from = bucket.get("from")
                    range_to = bucket.get("to")
                    filter_from = selected_price.get("min")
                    filter_to = selected_price.get("max")
                    if filter_from and filter_to:
                        # Check if ranges overlap
                        selected = not (range_to and range_to < filter_from) and not (range_from and range_from > filter_to)
                
                values.append(FacetValue(value, count, selected))
            
            if values:
                facets["price_ranges"] = Facet("price_ranges", values, "range")
        
        # Parse rating facets
        if "ratings" in aggregations:
            buckets = aggregations["ratings"].get("buckets", [])
            values = []
            selected_rating = selected_filters.get("rating", {})
            
            for bucket in buckets:
                value = bucket["key"]
                count = bucket["doc_count"]
                # Check if this range is selected
                selected = False
                if isinstance(selected_rating, dict):
                    range_from = bucket.get("from")
                    range_to = bucket.get("to")
                    filter_from = selected_rating.get("min")
                    filter_to = selected_rating.get("max")
                    if filter_from and filter_to:
                        selected = not (range_to and range_to < filter_from) and not (range_from and range_from > filter_to)
                
                values.append(FacetValue(value, count, selected))
            
            if values:
                facets["ratings"] = Facet("ratings", values, "range")
        
        # Parse availability facets
        if "availability" in aggregations:
            buckets = aggregations["availability"].get("buckets", [])
            values = []
            selected_availability = selected_filters.get("in_stock")
            
            for bucket in buckets:
                is_in_stock = bucket["key"] == 1 or bucket["key"] is True
                value = "In Stock" if is_in_stock else "Out of Stock"
                count = bucket["doc_count"]
                selected = (selected_availability is not None and 
                           ((is_in_stock and selected_availability) or 
                            (not is_in_stock and not selected_availability)))
                values.append(FacetValue(value, count, selected))
            
            if values:
                facets["availability"] = Facet("availability", values, "terms")
        
        # Parse attribute facets
        attribute_facets = {
            "attr_color": "Color",
            "attr_size": "Size",
            "attr_material": "Material",
            "attr_pattern": "Pattern",
            "attr_climate": "Climate"
        }
        
        for attr_key, attr_label in attribute_facets.items():
            if attr_key in aggregations:
                buckets = aggregations[attr_key].get("buckets", [])
                if buckets:  # Only add facet if there are values
                    values = []
                    selected_attrs = selected_filters.get(attr_key.replace("attr_", ""), [])
                    if not isinstance(selected_attrs, list):
                        selected_attrs = [selected_attrs] if selected_attrs else []
                    
                    for bucket in buckets:
                        value = bucket["key"]
                        count = bucket["doc_count"]
                        selected = value in selected_attrs
                        values.append(FacetValue(value, count, selected))
                    
                    if values:
                        facets[attr_key.replace("attr_", "")] = Facet(attr_label, values, "terms")
        
        return facets
    
    def get_facets_for_context(
        self,
        query: str,
        category: Optional[str] = None
    ) -> List[str]:
        """
        Get facet types relevant to the search context
        
        Args:
            query: Search query
            category: Product category (if known)
            
        Returns:
            List of facet type names to include
        """
        # Default facets - always include ratings and attributes
        facet_types = ["category", "brand", "price", "availability", "rating", "attributes"]
        
        # Context-aware: different facets per category
        # This is a simple example - can be enhanced with ML
        if category:
            # For electronics, might want more attribute facets
            # For clothing, might want size/color facets
            pass
        
        return facet_types

