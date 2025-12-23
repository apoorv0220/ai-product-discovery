"""
Merchandising Rules Engine
Implements rule evaluation and application for search result manipulation
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from shared.models.merchandising import MerchandisingRule
from core.database import get_async_session

logger = logging.getLogger(__name__)


class MerchandisingRulesEngine:
    """
    Merchandising rules engine for applying merchant-controlled search result manipulation
    
    Features:
    - Rule evaluation with condition matching
    - Boost application via Elasticsearch function_score
    - Product pinning to specific positions
    - Product hiding (filtering)
    - Redis caching for performance
    - Priority-based conflict resolution
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize merchandising rules engine
        
        Args:
            redis_client: Optional Redis client for caching
        """
        self.redis_client = redis_client
        self.cache_ttl = 300  # 5 minutes
        self.cache_prefix = "merchandising_rules"
    
    async def load_active_rules(
        self,
        merchant_id: int,
        use_cache: bool = True
    ) -> List[MerchandisingRule]:
        """
        Load active merchandising rules for a merchant
        
        Args:
            merchant_id: Merchant ID
            use_cache: Whether to use Redis cache
            
        Returns:
            List of active MerchandisingRule objects
        """
        cache_key = f"{self.cache_prefix}:{merchant_id}"
        
        # Try cache first
        if use_cache and self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    logger.debug(f"Cache hit for merchandising rules: merchant_id={merchant_id}")
                    rules_data = json.loads(cached_data)
                    # Convert dicts back to rule objects (simplified - in production, use proper serialization)
                    # For now, we'll fetch from DB but cache the IDs for faster lookup
                    rule_ids = [r.get("id") for r in rules_data]
                    if rule_ids:
                        async with get_async_session() as session:
                            result = await session.execute(
                                select(MerchandisingRule).where(
                                    and_(
                                        MerchandisingRule.id.in_(rule_ids),
                                        MerchandisingRule.merchant_id == merchant_id,
                                        MerchandisingRule.is_active == True
                                    )
                                )
                            )
                            rules = list(result.scalars().all())
                            return rules
            except Exception as e:
                logger.warning(f"Cache read failed, falling back to DB", error=str(e))
        
        # Fetch from database
        async with get_async_session() as session:
            result = await session.execute(
                select(MerchandisingRule).where(
                    and_(
                        MerchandisingRule.merchant_id == merchant_id,
                        MerchandisingRule.is_active == True
                    )
                ).order_by(MerchandisingRule.priority.desc())
            )
            rules = list(result.scalars().all())
        
        # Cache the rules
        if use_cache and self.redis_client and rules:
            try:
                # Cache rule metadata (IDs and basic info)
                rules_data = [
                    {
                        "id": rule.id,
                        "rule_type": rule.rule_type,
                        "priority": rule.priority,
                        "conditions": rule.conditions,
                        "action_config": rule.action_config
                    }
                    for rule in rules
                ]
                await self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(rules_data)
                )
                logger.debug(f"Cached {len(rules)} merchandising rules for merchant_id={merchant_id}")
            except Exception as e:
                logger.warning(f"Cache write failed", error=str(e))
        
        return rules
    
    async def invalidate_cache(self, merchant_id: int) -> None:
        """
        Invalidate cache for a merchant's rules
        
        Args:
            merchant_id: Merchant ID
        """
        if self.redis_client:
            cache_key = f"{self.cache_prefix}:{merchant_id}"
            try:
                await self.redis_client.delete(cache_key)
                logger.info(f"Invalidated merchandising rules cache for merchant_id={merchant_id}")
            except Exception as e:
                logger.warning(f"Cache invalidation failed", error=str(e))
    
    def evaluate_rules(
        self,
        query: str,
        context: Dict[str, Any],
        rules: List[MerchandisingRule]
    ) -> Dict[str, List[MerchandisingRule]]:
        """
        Evaluate rules and return matched rules by type
        
        Args:
            query: Search query string
            context: Additional context (categories, product_ids, etc.)
            rules: List of rules to evaluate
            
        Returns:
            Dictionary with rule types as keys and matched rules as values:
            {
                "boost": [rule1, rule2, ...],
                "pin": [rule3, ...],
                "hide": [rule4, ...]
            }
        """
        matched = {"boost": [], "pin": [], "hide": []}
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if self._match_condition(rule.conditions, query, context):
                matched[rule.rule_type].append(rule)
                logger.debug(
                    f"Rule matched: id={rule.id}, type={rule.rule_type}, "
                    f"priority={rule.priority}, name={rule.name}"
                )
        
        logger.info(
            f"Evaluated {len(rules)} rules, matched: "
            f"boost={len(matched['boost'])}, pin={len(matched['pin'])}, hide={len(matched['hide'])}"
        )
        
        return matched
    
    def _match_condition(
        self,
        condition: Dict,
        query: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Match a condition against query and context
        
        Args:
            condition: Condition dictionary with type, operator, value
            query: Search query string
            context: Additional context
            
        Returns:
            True if condition matches, False otherwise
        """
        condition_type = condition.get("type")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if condition_type == "query_match":
            query_lower = query.lower().strip()
            value_lower = str(value).lower().strip()
            
            if operator == "exact":
                return query_lower == value_lower
            elif operator == "contains":
                return value_lower in query_lower
            else:
                logger.warning(f"Unknown query_match operator: {operator}")
                return False
        
        elif condition_type == "category":
            categories = context.get("categories", [])
            if not isinstance(categories, list):
                categories = [categories] if categories else []
            
            if operator == "equals":
                return str(value) in [str(c) for c in categories]
            elif operator == "in":
                if isinstance(value, list):
                    return any(str(v) in [str(c) for c in categories] for v in value)
                else:
                    return str(value) in [str(c) for c in categories]
            else:
                logger.warning(f"Unknown category operator: {operator}")
                return False
        
        elif condition_type == "product_id":
            product_ids = context.get("product_ids", [])
            if not isinstance(product_ids, list):
                product_ids = [product_ids] if product_ids else []
            
            if operator == "equals":
                return str(value) in [str(pid) for pid in product_ids]
            elif operator == "in":
                if isinstance(value, list):
                    return any(str(v) in [str(pid) for pid in product_ids] for v in value)
                else:
                    return str(value) in [str(pid) for pid in product_ids]
            else:
                logger.warning(f"Unknown product_id operator: {operator}")
                return False
        
        else:
            logger.warning(f"Unknown condition type: {condition_type}")
            return False
    
    def apply_boosts(
        self,
        es_query: Dict,
        boost_rules: List[MerchandisingRule]
    ) -> Dict:
        """
        Add boost functions to Elasticsearch query
        
        Args:
            es_query: Elasticsearch query dictionary
            boost_rules: List of boost rules to apply
            
        Returns:
            Modified Elasticsearch query with boost functions
        """
        if not boost_rules:
            return es_query
        
        # Get existing function_score or create new
        query_dict = es_query.get("query", {})
        
        if "function_score" not in query_dict:
            # Wrap existing query in function_score
            original_query = query_dict
            es_query["query"] = {
                "function_score": {
                    "query": original_query,
                    "functions": [],
                    "score_mode": "sum",  # Additive boosts
                    "boost_mode": "multiply"
                }
            }
        
        functions = es_query["query"]["function_score"]["functions"]
        
        # Add boost functions for each rule
        for rule in boost_rules:
            boost_factor = rule.action_config.get("boost_factor", 1.0)
            # Cap at 10.0, minimum 0.1
            boost_factor = min(10.0, max(0.1, float(boost_factor)))
            
            # Create filter based on rule conditions
            filter_clause = self._build_boost_filter(rule.conditions)
            
            if filter_clause:
                functions.append({
                    "filter": filter_clause,
                    "weight": boost_factor
                })
                logger.debug(
                    f"Added boost function: rule_id={rule.id}, "
                    f"boost_factor={boost_factor}, filter={filter_clause}"
                )
        
        return es_query
    
    def _build_boost_filter(self, conditions: Dict) -> Optional[Dict]:
        """
        Build Elasticsearch filter from rule conditions
        
        Args:
            conditions: Condition dictionary
            
        Returns:
            Elasticsearch filter clause or None
        """
        condition_type = conditions.get("type")
        operator = conditions.get("operator")
        value = conditions.get("value")
        
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
        # So we'll apply boosts differently - this is handled in query builder
        return None
    
    def apply_pinning(
        self,
        results: List[Dict],
        pin_rules: List[MerchandisingRule]
    ) -> List[Dict]:
        """
        Apply pinning rules to reorder results
        
        Args:
            results: List of search result dictionaries
            pin_rules: List of pin rules to apply
            
        Returns:
            Reordered results with pinned products in specified positions
        """
        if not pin_rules:
            return results
        
        # Sort pin rules by position (ascending)
        pin_rules = sorted(
            pin_rules,
            key=lambda r: r.action_config.get("position", 999)
        )
        
        # Create mapping: position -> product_id
        pinned_products = {}
        for rule in pin_rules:
            position = rule.action_config.get("position", 1)
            product_id = str(rule.action_config.get("product_id", ""))
            if product_id and position not in pinned_products:
                pinned_products[position] = product_id
        
        if not pinned_products:
            return results
        
        # Separate pinned and non-pinned results
        pinned_results = []
        non_pinned_results = []
        pinned_ids = set(pinned_products.values())
        
        for result in results:
            product_id = str(result.get("product_id", ""))
            if product_id in pinned_ids:
                pinned_results.append((product_id, result))
            else:
                non_pinned_results.append(result)
        
        # Build final result list
        final_results = []
        max_position = max(pinned_products.keys()) if pinned_products else 0
        
        for pos in range(1, max_position + 1):
            if pos in pinned_products:
                # Find and insert pinned product
                product_id = pinned_products[pos]
                pinned_item = next(
                    (r for pid, r in pinned_results if pid == product_id),
                    None
                )
                if pinned_item:
                    final_results.append(pinned_item[1])
                # Fill with non-pinned if no pinned product found
                elif non_pinned_results:
                    final_results.append(non_pinned_results.pop(0))
            else:
                # Fill with non-pinned
                if non_pinned_results:
                    final_results.append(non_pinned_results.pop(0))
        
        # Add remaining non-pinned results
        final_results.extend(non_pinned_results)
        
        logger.info(
            f"Applied pinning: {len(pinned_products)} positions, "
            f"pinned {len([r for r in final_results if str(r.get('product_id', '')) in pinned_ids])} products"
        )
        
        return final_results
    
    def apply_hiding(
        self,
        results: List[Dict],
        hide_rules: List[MerchandisingRule]
    ) -> List[Dict]:
        """
        Apply hiding rules to filter out products
        
        Args:
            results: List of search result dictionaries
            hide_rules: List of hide rules to apply
            
        Returns:
            Filtered results with hidden products removed
        """
        if not hide_rules:
            return results
        
        # Collect all product IDs to hide
        hidden_ids = set()
        for rule in hide_rules:
            # Extract product IDs from rule conditions
            condition = rule.conditions
            if condition.get("type") == "product_id":
                value = condition.get("value")
                if isinstance(value, list):
                    hidden_ids.update(str(v) for v in value)
                else:
                    hidden_ids.add(str(value))
        
        if not hidden_ids:
            return results
        
        # Filter out hidden products
        filtered_results = [
            r for r in results
            if str(r.get("product_id", "")) not in hidden_ids
        ]
        
        logger.info(
            f"Applied hiding: {len(hidden_ids)} products hidden, "
            f"{len(results)} -> {len(filtered_results)} results"
        )
        
        return filtered_results


