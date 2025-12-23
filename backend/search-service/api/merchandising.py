"""
Merchandising Rules API
Endpoints for managing search result manipulation rules
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import List, Optional
from sqlalchemy import select, and_
import structlog

from shared.middleware.auth import get_merchant_id
from shared.models.merchandising import MerchandisingRule
from core.database import get_async_session
from schemas.merchandising import (
    MerchandisingRuleCreate,
    MerchandisingRuleUpdate,
    MerchandisingRuleResponse,
    RulePreviewRequest,
    RulePreviewResponse
)
from core.merchandising_engine import MerchandisingRulesEngine
from api.search import _perform_keyword_search

logger = structlog.get_logger()

router = APIRouter()


async def get_merchandising_engine(request: Request) -> MerchandisingRulesEngine:
    """Get merchandising engine with Redis client"""
    redis_client = getattr(request.app.state, "search_cache", None)
    if redis_client:
        redis_client = redis_client.redis if hasattr(redis_client, "redis") else None
    return MerchandisingRulesEngine(redis_client=redis_client)


@router.post("/", response_model=MerchandisingRuleResponse, status_code=201)
async def create_rule(
    rule_data: MerchandisingRuleCreate,
    request: Request
):
    """Create a new merchandising rule"""
    merchant_id = get_merchant_id(request)
    
    async with get_async_session() as db:
        try:
            # Create rule
            rule = MerchandisingRule(
                merchant_id=merchant_id,
                name=rule_data.name,
                description=rule_data.description,
                rule_type=rule_data.rule_type,
                priority=rule_data.priority,
                is_active=rule_data.is_active,
                trigger_conditions=rule_data.trigger_conditions,
                target_conditions=rule_data.target_conditions,
                action_config=rule_data.action_config
            )
            
            db.add(rule)
            await db.commit()
            await db.refresh(rule)
            
            # Invalidate cache
            engine = await get_merchandising_engine(request)
            await engine.invalidate_cache(merchant_id)
            
            logger.info(f"Created merchandising rule: id={rule.id}, name={rule.name}, type={rule.rule_type}")
            
            return MerchandisingRuleResponse.model_validate(rule)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create rule", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to create rule: {str(e)}")


@router.get("/", response_model=List[MerchandisingRuleResponse])
async def list_rules(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    rule_type: Optional[str] = Query(None, description="Filter by rule type")
):
    """List merchandising rules for the merchant"""
    merchant_id = get_merchant_id(request)
    
    async with get_async_session() as db:
        try:
            query = select(MerchandisingRule).where(
                MerchandisingRule.merchant_id == merchant_id
            )
            
            if is_active is not None:
                query = query.where(MerchandisingRule.is_active == is_active)
            
            if rule_type:
                query = query.where(MerchandisingRule.rule_type == rule_type)
            
            query = query.order_by(MerchandisingRule.priority.desc(), MerchandisingRule.created_at.desc())
            query = query.offset(skip).limit(limit)
            
            result = await db.execute(query)
            rules = result.scalars().all()
            
            return [MerchandisingRuleResponse.model_validate(rule) for rule in rules]
            
        except Exception as e:
            logger.error(f"Failed to list rules", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to list rules: {str(e)}")


@router.get("/{rule_id}", response_model=MerchandisingRuleResponse)
async def get_rule(
    rule_id: int,
    request: Request
):
    """Get a specific merchandising rule"""
    merchant_id = get_merchant_id(request)
    
    async with get_async_session() as db:
        try:
            result = await db.execute(
                select(MerchandisingRule).where(
                    and_(
                        MerchandisingRule.id == rule_id,
                        MerchandisingRule.merchant_id == merchant_id
                    )
                )
            )
            rule = result.scalar_one_or_none()
            
            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            return MerchandisingRuleResponse.model_validate(rule)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get rule", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to get rule: {str(e)}")


@router.put("/{rule_id}", response_model=MerchandisingRuleResponse)
async def update_rule(
    rule_id: int,
    rule_data: MerchandisingRuleUpdate,
    request: Request
):
    """Update an existing merchandising rule"""
    merchant_id = get_merchant_id(request)
    
    async with get_async_session() as db:
        try:
            result = await db.execute(
                select(MerchandisingRule).where(
                    and_(
                        MerchandisingRule.id == rule_id,
                        MerchandisingRule.merchant_id == merchant_id
                    )
                )
            )
            rule = result.scalar_one_or_none()
            
            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            # Update fields
            update_data = rule_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(rule, field, value)
            
            await db.commit()
            await db.refresh(rule)
            
            # Invalidate cache
            engine = await get_merchandising_engine(request)
            await engine.invalidate_cache(merchant_id)
            
            logger.info(f"Updated merchandising rule: id={rule.id}, name={rule.name}")
            
            return MerchandisingRuleResponse.model_validate(rule)
            
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update rule", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to update rule: {str(e)}")


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: int,
    request: Request
):
    """Delete a merchandising rule"""
    merchant_id = get_merchant_id(request)
    
    async with get_async_session() as db:
        try:
            result = await db.execute(
                select(MerchandisingRule).where(
                    and_(
                        MerchandisingRule.id == rule_id,
                        MerchandisingRule.merchant_id == merchant_id
                    )
                )
            )
            rule = result.scalar_one_or_none()
            
            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            await db.delete(rule)
            await db.commit()
            
            # Invalidate cache
            engine = await get_merchandising_engine(request)
            await engine.invalidate_cache(merchant_id)
            
            logger.info(f"Deleted merchandising rule: id={rule_id}")
            
            return None
            
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete rule", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")


@router.post("/{rule_id}/preview", response_model=RulePreviewResponse)
async def preview_rule(
    rule_id: int,
    preview_request: RulePreviewRequest,
    request: Request
):
    """Preview how a rule would affect search results"""
    merchant_id = get_merchant_id(request)
    
    async with get_async_session() as db:
        try:
            # Get rule
            result = await db.execute(
                select(MerchandisingRule).where(
                    and_(
                        MerchandisingRule.id == rule_id,
                        MerchandisingRule.merchant_id == merchant_id
                    )
                )
            )
            rule = result.scalar_one_or_none()
            
            if not rule:
                raise HTTPException(status_code=404, detail="Rule not found")
            
            # Evaluate rule
            engine = await get_merchandising_engine(request)
            context = {"merchant_id": merchant_id, "categories": []}

            # Use trigger_conditions if present, otherwise fall back to target_conditions or old conditions
            trigger_conditions = getattr(rule, 'trigger_conditions', None)
            if trigger_conditions is None:
                trigger_conditions = getattr(rule, 'target_conditions', None) or getattr(rule, 'conditions', None)

            would_match = trigger_conditions and engine._match_condition(trigger_conditions, preview_request.query, context)
            
            # If rule would match, get affected products
            matched_products = []
            if would_match:
                try:
                    # Perform a test search to see which products would be affected
                    es_client = request.app.state.elasticsearch
                    search_cache = getattr(request.app.state, "search_cache", None)
                    
                    # Build context with categories if available
                    # For preview, we'll do a simple search
                    result_data = await _perform_keyword_search(
                        preview_request.query,
                        merchant_id,
                        preview_request.limit,
                        0,
                        None,
                        es_client,
                        search_cache,
                        include_facets=False,
                        merchandising_rules=[rule] if rule.rule_type == "boost" else None
                    )
                    
                    # Extract product IDs that would be affected
                    if rule.rule_type == "pin":
                        product_id = rule.action_config.get("product_id")
                        if product_id:
                            matched_products = [
                                r for r in result_data.get("results", [])
                                if str(r.get("product_id", "")) == str(product_id)
                            ]
                    elif rule.rule_type == "hide":
                        # Find products that match hide condition
                        target_conditions = getattr(rule, 'target_conditions', None) or getattr(rule, 'conditions', None)
                        if target_conditions and target_conditions.get("type") == "product_id":
                            value = target_conditions.get("value")
                            product_ids = [value] if not isinstance(value, list) else value
                            matched_products = [
                                r for r in result_data.get("results", [])
                                if str(r.get("product_id", "")) in [str(pid) for pid in product_ids]
                            ]
                    else:  # boost
                        # For boost, we can't easily determine which products would be boosted
                        # without running the full query. Show a message instead.
                        matched_products = []
                    
                except Exception as e:
                    logger.warning(f"Failed to get preview products", error=str(e))
                    matched_products = []
            
            message = (
                f"Rule would {'match' if would_match else 'not match'} the query '{preview_request.query}'. "
                f"{len(matched_products)} product(s) would be affected."
            )
            
            return RulePreviewResponse(
                rule_id=rule.id,
                rule_name=rule.name,
                query=preview_request.query,
                would_match=would_match,
                matched_products=matched_products,
                message=message
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to preview rule", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to preview rule: {str(e)}")
